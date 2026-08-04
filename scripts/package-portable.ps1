$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$exe = Join-Path $root "src-tauri\target\release\sql-oj.exe"
if (-not (Test-Path $exe)) {
    Write-Host "未找到 $exe，请先运行: npm run tauri:build:portable"
    exit 1
}
$outDir = Join-Path $root "dist-portable"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$dest = Join-Path $outDir "SQL-OJ_0.1.0_x64-portable.exe"
Copy-Item $exe $dest -Force
Write-Host "免安装版: $dest"
Write-Host "大小: $((Get-Item $dest).Length / 1MB) MB"
