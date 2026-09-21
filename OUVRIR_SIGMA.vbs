Option Explicit
Dim shell, fso, root, pythonw, server, http, deadline, url
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
server = root & "\run_server.py"
url = "http://127.0.0.1:8000/dashboard/"

If Not fso.FileExists(pythonw) Then
  MsgBox "SIGMA n'est pas encore prepare. Executez une seule fois setup.bat, ou utilisez SIGMA-Setup.exe pour l'installation commerciale.", 48, "SIGMA"
  WScript.Quit 10
End If

If Not IsSigmaOnline() Then
  shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & server & Chr(34), 0, False
End If

deadline = DateAdd("s", 30, Now)
Do
  If IsSigmaOnline() Then Exit Do
  WScript.Sleep 500
Loop While Now < deadline

shell.Run url, 1, False

Function IsSigmaOnline()
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  http.Open "GET", "http://127.0.0.1:8000/api/health/live", False
  http.send
  IsSigmaOnline = (Err.Number = 0 And http.Status = 200)
  Err.Clear
  On Error GoTo 0
End Function
