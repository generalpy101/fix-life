[Setup]
AppName=FixLife
AppVersion=1.0
DefaultDirName={pf}\FixLife
DefaultGroupName=FixLife
OutputBaseFilename=FixLifeInstaller
Compression=lzma
SolidCompression=yes
DisableDirPage=no
DisableProgramGroupPage=no
PrivilegesRequired=admin

[Files]
Source: "dist\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FixLife"; Filename: "{app}\FixLife.exe"
Name: "{group}\Uninstall FixLife"; Filename: "{uninstallexe}"
Name: "{commonstartup}\FixLife"; Filename: "{app}\FixLife.exe"; Comment: "Start FixLife on boot"
Name: "{userdesktop}\Fix Life"; Filename: "{app}\FixLife.exe";

[Code]
procedure SetElevationBit(Filename: string);
var
  Buffer: string;
  Stream: TStream;
begin
  Filename := ExpandConstant(Filename);
  Log('Setting elevation bit for ' + Filename);

  Stream := TFileStream.Create(FileName, fmOpenReadWrite);
  try
    Stream.Seek(21, soFromBeginning);
    SetLength(Buffer, 1);
    Stream.ReadBuffer(Buffer, 1);
    Buffer[1] := Chr(Ord(Buffer[1]) or $20);
    Stream.Seek(-1, soFromCurrent);
    Stream.WriteBuffer(Buffer, 1);
  finally
    Stream.Free;
  end;
end;