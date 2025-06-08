# build.ps1
param (
    [switch]$NoConsole
)

$ErrorActionPreference = "Stop"

# # Clean previous build
# Remove-Item -Recurse -Force dist -ErrorAction Ignore

# Set common Nuitka options
$nuitkaArgs = @(
    "main.py",
    "--standalone",
    "--output-dir=dist",
    "--remove-output",
    "--include-data-dir=dashboard/templates=dashboard/templates",
    "--include-data-dir=dashboard/static=dashboard/static",
    "--include-data-dir=activity=activity",
    "--include-data-dir=data=data",
    "--include-data-dir=${env:VIRTUAL_ENV}/Lib/site-packages/werkzeug/debug/shared=werkzeug/debug/shared"
    "--python-flag=nosite",
    "--jobs=$([Environment]::ProcessorCount)",
    "--windows-icon-from-ico=img/icons/fixlife.ico"
)

# Add --windows-disable-console if NoConsole flag is passed
if ($NoConsole) {
    $nuitkaArgs += "--windows-console-mode=disable"
} else {
    $nuitkaArgs += "--windows-console-mode=force"
}

Write-Host '🔨 Building project with Nuitka...'
python -m nuitka @nuitkaArgs

# Check if the build was successful
if (-Not (Test-Path "dist/main.dist/main.exe")) {
    Write-Error "❌ Build failed. Please check the output for errors."
    exit 1
}

# Rename dist/main.dist/main.exe to something friendly
Move-Item "dist/main.dist/main.exe" -Destination "dist/main.dist/FixLife.exe"

$innoScriptPath = "installer.iss"
if (-Not (Test-Path $innoScriptPath)) {
    Write-Error "❌ Inno Setup script not found at: $innoScriptPath. Please check your script path."
    exit 1
}
# Compile the installer
$innoCompiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'

if (-Not (Test-Path $innoCompiler)) {
    Write-Error "❌ Inno Setup Compiler not found at: $innoCompiler. Please check your installation."
    exit 1
}

Write-Host '📦 Creating Windows Installer using Inno Setup...'

# Use call operator with array syntax
& "$innoCompiler" "$innoScriptPath"

Write-Host "✅ Installer build complete. Check 'dist\Output' or Inno Setup's output folder."
