; ============================================================
; Script de Inno Setup para RedMovilPOS
; ============================================================
; Para compilar este instalador necesitas Inno Setup:
; https://jrsoftware.org/isinfo.php
; ============================================================

#define MyAppName "RedMovilPOS"
#define MyAppVersion "5.0.3"
#define MyAppPublisher "RABI EL-OUAHIDI Y OTROS ESPJ"
#define MyAppExeName "RedMovilPOS.exe"

[Setup]
; Identificador unico de la aplicacion
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Carpeta de salida del instalador
OutputDir=..\instalador_output
OutputBaseFilename=RedMovilPOS_Setup_v{#MyAppVersion}
; Icono del instalador
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Requiere privilegios de administrador para instalar
PrivilegesRequired=admin
; Arquitectura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Crear desinstalador
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Archivos de la aplicacion compilada
Source: "..\dist\RedMovilPOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: No incluir la carpeta generador_claves (es solo para el desarrollador)

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Ejecutar la aplicacion al finalizar la instalacion
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Forzar eliminacion de carpetas que pueden quedar
Type: filesandordirs; Name: "{app}\_internal\data"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}"

[Code]
var
  EliminarDatos: Boolean;

// Verificar si ya esta instalado y ofrecer desinstalar primero
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstallString: String;
begin
  Result := True;

  // Buscar instalacion anterior
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1',
    'UninstallString', UninstallString) then
  begin
    if MsgBox('Ya existe una version de {#MyAppName} instalada.' + #13#10 + #13#10 +
              'Desea desinstalar la version anterior antes de continuar?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

// Crear carpeta de datos al instalar
procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{commonappdata}\Facturar');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
  end;
end;

// ============================================================
// DESINSTALACION - Preguntar si eliminar datos
// ============================================================

function InitializeUninstall(): Boolean;
begin
  Result := True;
  EliminarDatos := False;

  // Preguntar al usuario si desea eliminar los datos
  if MsgBox('ATENCION: Se va a desinstalar {#MyAppName}.' + #13#10 + #13#10 +
            'Desea ELIMINAR TAMBIEN todos los datos del programa?' + #13#10 +
            '(Base de datos, facturas PDF, tickets, contratos, licencia...)' + #13#10 + #13#10 +
            'Si pulsa SI, se eliminaran TODOS los datos permanentemente.' + #13#10 +
            'Si pulsa NO, los datos se conservaran para una futura reinstalacion.',
            mbConfirmation, MB_YESNO) = IDYES then
  begin
    // Confirmacion adicional por seguridad
    if MsgBox('CONFIRMACION FINAL' + #13#10 + #13#10 +
              'Esta seguro de que desea eliminar TODOS los datos?' + #13#10 +
              'Esta accion NO se puede deshacer.' + #13#10 + #13#10 +
              '- Base de datos con clientes, productos, ventas...' + #13#10 +
              '- Facturas y tickets en PDF' + #13#10 +
              '- Contratos de compra' + #13#10 +
              '- Ordenes de reparacion' + #13#10 +
              '- Configuracion y licencia',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      EliminarDatos := True;
    end;
  end;
end;

// Eliminar datos despues de la desinstalacion
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if EliminarDatos then
    begin
      DataDir := ExpandConstant('{commonappdata}\Facturar');

      // Eliminar toda la carpeta de datos
      if DirExists(DataDir) then
      begin
        DelTree(DataDir, True, True, True);
      end;

      MsgBox('Desinstalacion completa.' + #13#10 + #13#10 +
             'Se han eliminado todos los datos del programa.',
             mbInformation, MB_OK);
    end
    else
    begin
      MsgBox('Desinstalacion completa.' + #13#10 + #13#10 +
             'Los datos del programa se han conservado en:' + #13#10 +
             ExpandConstant('{commonappdata}\Facturar') + #13#10 + #13#10 +
             'Puede reinstalar el programa para recuperar sus datos.',
             mbInformation, MB_OK);
    end;
  end;
end;

// Verificar que el programa no este en ejecucion antes de desinstalar
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  // Podrias añadir aqui verificacion de proceso en ejecucion
end;
