param(
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)
. (Join-Path $PSScriptRoot "env.ps1")
$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\material_db_cli.py"
& $Py $Cli --db $DbPath init
