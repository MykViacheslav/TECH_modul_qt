$ErrorActionPreference = "Stop"

$Proj = Split-Path -Parent $PSScriptRoot
$Src  = Join-Path $Proj "src"
$Py   = Join-Path (Join-Path $Proj ".venv") "Scripts\python.exe"

if(-not (Test-Path $Py)){
  throw "Missing venv python: $Py"
}

$env:PYTHONPATH = $Src

$DbDir = Join-Path $Proj "data"
$Db    = Join-Path $DbDir "tech.db"

$Cli = Join-Path $Src "tools\module_db_cli.py"
if(-not (Test-Path $Cli)){
  throw "Missing CLI: $Cli"
}
