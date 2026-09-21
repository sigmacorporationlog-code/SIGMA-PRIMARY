#define MyAppName "SIGMA"
; La version réelle est régénérée depuis release.json par build_windows.ps1
; dans version.iss.inc. Le #define de repli garde le script compilable seul.
#include "version.iss.inc"
#ifndef MyAppVersion
  #define MyAppVersion "4.46.0"
#endif
#define MyAppExeName "SIGMA-Server.exe"
#define MyServiceName "SIGMAPrimaireServer"
#define MyFirewallRuleName "SIGMA Server (TCP 8000)"

[Setup]
AppId={{A2A4E5E6-6D0C-4E2C-9C5D-445100000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SIGMA
DefaultDirName={autopf}\SIGMA
DefaultGroupName=SIGMA
OutputDir=..\release_out\{#MyAppVersion}
OutputBaseFilename=SIGMA-{#MyAppVersion}-Setup
SetupIconFile=..\assets\sigma.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName=SIGMA {#MyAppVersion}

[Code]
procedure PrepareServiceForUpgrade;
var
  ResultCode: Integer;
begin
  { Stop/delete the previous service BEFORE Inno Setup replaces the EXE. }
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\sc.exe'), 'delete {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    PrepareServiceForUpgrade;
end;

[Files]
; Build PyInstaller « onedir » : l'exécutable et son dossier _internal
; (interpréteur Python, modules natifs, static/, alembic/) sont copiés tels
; quels. Le poste cible n'a donc rien à installer.
Source: "..\dist\SIGMA-Server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\open_sigma.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\sigma.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\SIGMA"

[Run]
; Initialise les secrets et la configuration hors de Program Files.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--setup"; Flags: runhidden waituntilterminated
; Protège les données persistantes (base, .env, médias) contre la lecture
; par les comptes utilisateurs standards. Les SID rendent la règle
; indépendante de la langue de Windows.
Filename: "{sys}\icacls.exe"; Parameters: """{commonappdata}\SIGMA"" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F"; Flags: runhidden waituntilterminated
; Remplace proprement un ancien service si nécessaire.
Filename: "{sys}\sc.exe"; Parameters: "stop {#MyServiceName}"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{sys}\sc.exe"; Parameters: "delete {#MyServiceName}"; Flags: runhidden waituntilterminated skipifdoesntexist
; Le serveur tourne en arrière-plan via le Gestionnaire des services Windows.
; Endpoint du pilote : http://127.0.0.1:8000/dashboard/ (localport=8000)
; Le chemin de binPath doit rester entre guillemets ÉCHAPPÉS, sinon sc.exe
; coupe « C:\Program Files\... » sur l'espace et le service ne démarre pas.
Filename: "{sys}\sc.exe"; Parameters: "create {#MyServiceName} binPath= ""\""{app}\{#MyAppExeName}\"" --service"" start= auto DisplayName= ""SIGMA Server"""; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "description {#MyServiceName} ""Serveur local SIGMA — gestion scolaire"""; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "failure {#MyServiceName} reset= 86400 actions= restart/5000/restart/15000/restart/60000"; Flags: runhidden waituntilterminated
; Ouvre le port 8000 pour les postes clients du LAN. Sans cette règle,
; BIND_HOST=0.0.0.0 ne suffit pas : le pare-feu Windows bloque par défaut
; les connexions entrantes vers un nouveau programme. On supprime d'abord
; une règle du même nom (résidu d'une réinstallation) pour rester
; idempotent, comme pour le service ci-dessus.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallRuleName}"""; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#MyFirewallRuleName}"" dir=in action=allow protocol=TCP localport=8000 profile=private,domain"; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "start {#MyServiceName}"; Flags: runhidden waituntilterminated
; Affiche automatiquement les identifiants bootstrap pour le premier
; administrateur — sans case à cocher à retrouver soi-même sur la dernière
; page de l'assistant (l'ancienne version, avec les indicateurs postinstall/
; unchecked, décochait cette option par défaut : un simple clic sur
; « Terminer » sans y prêter attention faisait manquer le mot de passe).
; skipifsilent : reste silencieux lors d'une installation automatisée
; (/VERYSILENT), qui n'a de toute façon personne pour lire Notepad.
Filename: "{sys}\notepad.exe"; Parameters: """{commonappdata}\SIGMA\first-run-credentials.txt"""; Flags: nowait skipifsilent
; Attend SIGMA puis ouvre le navigateur sans afficher de terminal.
Filename: "{sys}\wscript.exe"; Parameters: """{app}\open_sigma.vbs"""; Flags: runhidden nowait

[Icons]
; Les deux raccourcis (Bureau et menu Démarrer) lancent le même script VBS
; silencieux, mais IconFilename force explicitement l'icône Sigma vert/orange
; de la charte graphique au lieu de l'icône générique de wscript.exe.
; C'est aussi cette icône qui apparaît si l'utilisateur épingle le raccourci
; à la barre des tâches ("Épingler à la barre des tâches" dans le clic droit).
Name: "{autodesktop}\SIGMA"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\open_sigma.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\sigma.ico"; Comment: "Ouvrir SIGMA"
Name: "{group}\SIGMA"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\open_sigma.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\sigma.ico"; Comment: "Ouvrir SIGMA"
Name: "{group}\Désinstaller SIGMA"; Filename: "{uninstallexe}"; IconFilename: "{app}\sigma.ico"

[UninstallRun]
Filename: "{sys}\sc.exe"; Parameters: "stop {#MyServiceName}"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{sys}\sc.exe"; Parameters: "delete {#MyServiceName}"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallRuleName}"""; Flags: runhidden waituntilterminated skipifdoesntexist
