Option Explicit

Dim shell, fso, root, ps, logDir, launcherLog, cmd, rc, errText
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
ps = root & "\build_windows.ps1"
logDir = root & "\release_out\build_logs"
launcherLog = logDir & "\launcher.log"

On Error Resume Next
If Not fso.FolderExists(logDir) Then fso.CreateFolder logDir
On Error GoTo 0

Dim logFile
On Error Resume Next
Set logFile = fso.OpenTextFile(launcherLog, 8, True, -1)
If Not logFile Is Nothing Then
    logFile.WriteLine Now & " | Lancement compilation : " & ps
    logFile.Close
End If
On Error GoTo 0

If Not fso.FileExists(ps) Then
    MsgBox "Le script de compilation SIGMA est introuvable." & vbCrLf & vbCrLf & ps, 16, "SIGMA - Compilation"
    WScript.Quit 10
End If

' Utilise le Windows PowerShell systeme, sans dependre du PATH utilisateur.
cmd = Chr(34) & shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe" & Chr(34) _
    & " -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File " _
    & Chr(34) & ps & Chr(34) & " -Clean"

On Error Resume Next
rc = shell.Run(cmd, 0, True)
errText = Err.Description
If Err.Number <> 0 Then
    Dim e
    e = Err.Number
    Err.Clear
    On Error GoTo 0
    MsgBox "Impossible de lancer la compilation SIGMA." & vbCrLf & vbCrLf & _
           "Erreur : " & e & vbCrLf & errText & vbCrLf & vbCrLf & _
           "Verifiez le fichier launcher.log dans :" & vbCrLf & logDir, 16, "SIGMA - Compilation"
    WScript.Quit 11
End If
On Error GoTo 0

If rc <> 0 Then
    MsgBox "La compilation SIGMA s'est arretee avec le code " & rc & "." & vbCrLf & vbCrLf & _
           "Aucune commande n'est a saisir." & vbCrLf & _
           "Le journal detaille se trouve ici :" & vbCrLf & logDir, 16, "SIGMA - Echec de compilation"
    WScript.Quit rc
End If

On Error Resume Next
Set logFile = fso.OpenTextFile(launcherLog, 8, True, -1)
If Not logFile Is Nothing Then
    logFile.WriteLine Now & " | Compilation terminee avec succes."
    logFile.Close
End If
On Error GoTo 0
MsgBox "Compilation SIGMA terminee avec succes." & vbCrLf & vbCrLf & _
       "Les fichiers produits se trouvent dans :" & vbCrLf & _
       root & "\release_out", 64, "SIGMA - Compilation terminee"
WScript.Quit 0
