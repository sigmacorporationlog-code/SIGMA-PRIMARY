"""Windows Service Control Manager adapter for SIGMA Server.

Uses only the Python standard library so the frozen commercial build does not
need pywin32. The service worker runs Uvicorn in-process and reacts to SCM
STOP/SHUTDOWN controls through a threading.Event.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import threading
from typing import Callable

SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_ACCEPT_SHUTDOWN = 0x00000004
SERVICE_START_PENDING = 0x00000002
SERVICE_RUNNING = 0x00000004
SERVICE_STOP_PENDING = 0x00000003
SERVICE_STOPPED = 0x00000001
NO_ERROR = 0
ERROR_FAILED_SERVICE_CONTROLLER_CONNECT = 1063

_HANDLER = ctypes.WINFUNCTYPE(None, wintypes.DWORD)
_SERVICE_MAIN = ctypes.WINFUNCTYPE(None, wintypes.DWORD, ctypes.POINTER(ctypes.LPWSTR))


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", wintypes.DWORD),
        ("dwCurrentState", wintypes.DWORD),
        ("dwControlsAccepted", wintypes.DWORD),
        ("dwWin32ExitCode", wintypes.DWORD),
        ("dwServiceSpecificExitCode", wintypes.DWORD),
        ("dwCheckPoint", wintypes.DWORD),
        ("dwWaitHint", wintypes.DWORD),
    ]


class SERVICE_TABLE_ENTRY(ctypes.Structure):
    _fields_ = [
        ("lpServiceName", wintypes.LPWSTR),
        ("lpServiceProc", _SERVICE_MAIN),
    ]


class WindowsServiceHost:
    """Small native SCM host around a SIGMA server worker."""

    def __init__(self, name: str, worker: Callable[[threading.Event], None]):
        self.name = name
        self.worker = worker
        self.stop_event = threading.Event()
        self._status_handle = None
        self._handler_ref = None
        self._main_ref = None
        self._worker_thread = None
        self._worker_error = None
        self._status = SERVICE_STATUS()

    def _set_status(self, state: int, exit_code: int = NO_ERROR) -> None:
        self._status.dwServiceType = SERVICE_WIN32_OWN_PROCESS
        self._status.dwCurrentState = state
        self._status.dwControlsAccepted = (
            0 if state in (SERVICE_START_PENDING, SERVICE_STOP_PENDING, SERVICE_STOPPED)
            else SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN
        )
        self._status.dwWin32ExitCode = exit_code
        self._status.dwServiceSpecificExitCode = 0
        self._status.dwCheckPoint = 0
        self._status.dwWaitHint = 5000 if state in (SERVICE_START_PENDING, SERVICE_STOP_PENDING) else 0
        if self._status_handle:
            advapi32 = ctypes.windll.advapi32
            advapi32.SetServiceStatus(self._status_handle, ctypes.byref(self._status))

    def _control(self, control: int) -> None:
        # SERVICE_CONTROL_STOP = 1, SERVICE_CONTROL_SHUTDOWN = 5
        if control in (1, 5):
            self._set_status(SERVICE_STOP_PENDING)
            self.stop_event.set()

    def _main(self, _argc: int, _argv) -> None:
        advapi32 = ctypes.windll.advapi32
        self._handler_ref = _HANDLER(self._control)
        advapi32.RegisterServiceCtrlHandlerW.restype = wintypes.HANDLE
        self._status_handle = advapi32.RegisterServiceCtrlHandlerW(self.name, self._handler_ref)
        if not self._status_handle:
            return

        self._set_status(SERVICE_START_PENDING)

        def guarded_worker() -> None:
            try:
                self.worker(self.stop_event)
            except BaseException as exc:
                # A worker crash must result in a non-zero service exit code
                # so SCM can apply the configured recovery actions.
                self._worker_error = exc
                self.stop_event.set()

        self._worker_thread = threading.Thread(target=guarded_worker, daemon=True)
        self._worker_thread.start()
        self._set_status(SERVICE_RUNNING)
        self._worker_thread.join()
        exit_code = 1 if self._worker_error is not None else NO_ERROR
        self._set_status(SERVICE_STOPPED, exit_code=exit_code)

    def run(self) -> int:
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("Le mode service Windows nécessite Windows.")

        self._main_ref = _SERVICE_MAIN(self._main)
        table = (SERVICE_TABLE_ENTRY * 2)()
        table[0].lpServiceName = self.name
        table[0].lpServiceProc = self._main_ref
        table[1].lpServiceName = None
        table[1].lpServiceProc = _SERVICE_MAIN()
        ok = ctypes.windll.advapi32.StartServiceCtrlDispatcherW(table)
        if not ok:
            error = ctypes.windll.kernel32.GetLastError()
            if error == ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
                raise RuntimeError("SIGMA-Server n'est pas lancé par le Gestionnaire de services Windows.")
            return int(error)
        return NO_ERROR
