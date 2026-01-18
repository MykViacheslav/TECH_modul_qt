param(
  [Parameter(Mandatory=$true)][string]$Anchor,
  [int]$Limit = 50,
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)

. (Join-Path $PSScriptRoot "env.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\module_db_cli.py"

& $Py $Cli --db $DbPath history --anchor $Anchor --limit $Limit
