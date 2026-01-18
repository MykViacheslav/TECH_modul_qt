param(
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db"),
  [int]$Limit = 200
)

. (Join-Path $PSScriptRoot "env.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\module_db_cli.py"

& $Py $Cli --db $DbPath list --limit $Limit
