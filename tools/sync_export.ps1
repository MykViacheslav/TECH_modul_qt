param(
  [string]$Out = (Join-Path (Split-Path $PSScriptRoot -Parent) "sync\tech_export.json"),
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)

. (Join-Path $PSScriptRoot "env.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\tech_sync_cli.py"

# Make sure imports work (tools.* live under src)
$env:PYTHONPATH = (Join-Path $Root "src")

& $Py $Cli --db $DbPath export --out $Out
