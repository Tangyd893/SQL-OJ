# Generate Tauri bundle icons from the in-app SVG source.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$svg = Join-Path $root 'public\icon.svg'
if (-not (Test-Path $svg)) {
  throw "missing icon source: $svg"
}

Push-Location $root
try {
  npx tauri icon $svg
  Write-Host "generated src-tauri/icons from $svg"
}
finally {
  Pop-Location
}
