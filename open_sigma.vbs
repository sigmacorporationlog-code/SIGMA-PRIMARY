Option Explicit
Dim shell, http, deadline, url, healthy
Set shell = CreateObject("WScript.Shell")
url = "http://127.0.0.1:8000/dashboard/"
deadline = DateAdd("s", 30, Now)
healthy = False
Do
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  http.Open "GET", "http://127.0.0.1:8000/api/health/live", False
  http.send
  If Err.Number = 0 And http.Status = 200 Then
    healthy = True
    Exit Do
  End If
  Err.Clear
  On Error GoTo 0
  WScript.Sleep 500
Loop While Now < deadline

If healthy Then
  shell.Run url, 1, False
Else
  MsgBox "SIGMA ne repond pas apres 30 secondes." & vbCrLf & vbCrLf & _
         "Verifiez que le service " SIGMA Server " est demarre dans Windows." & vbCrLf & _
         "Journal : %PROGRAMDATA%\SIGMA\sigma-service.log", 16, "SIGMA - Serveur indisponible"
End If
