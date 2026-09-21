Option Explicit
' Arret propre du paquet SIGMA portable.
' L'executable est compile sans console : il n'existe ni Ctrl+C ni icone de
' zone de notification. Ce script demande a SIGMA-Server.exe de s'arreter
' normalement (fermeture des connexions et de la base) plutot que de tuer le
' processus. En installation commerciale, le serveur est un service Windows :
' utilisez plutot services.msc, ce script n'y est pas necessaire.
Dim shell, fso, root, exePath, rc
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = root & "\SIGMA-Server.exe"

If Not fso.FileExists(exePath) Then
  MsgBox "SIGMA-Server.exe est introuvable a cote de ce script." & vbCrLf & vbCrLf & root, 48, "SIGMA - Arret"
  WScript.Quit 10
End If

rc = shell.Run(Chr(34) & exePath & Chr(34) & " --stop", 0, True)

If rc = 0 Then
  MsgBox "SIGMA est arrete.", 64, "SIGMA - Arret"
ElseIf rc = 2 Then
  MsgBox "Aucun serveur SIGMA en cours d'execution n'a repondu.", 48, "SIGMA - Arret"
Else
  MsgBox "L'arret de SIGMA a echoue (code " & rc & ").", 16, "SIGMA - Arret"
End If
WScript.Quit rc
