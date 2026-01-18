param(
  [Parameter(Mandatory=$true)][string]$In,
  [switch]$Overwrite,
  [switch]$NoHistory,
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)

. (Join-Path $PSScriptRoot "env.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\tech_sync_cli.py"

$env:PYTHONPATH = (Join-Path $Root "src")

$args = @($Cli, "--db", $DbPath, "import", "--in", $In)
if($Overwrite){ $args += "--overwrite" }
if($NoHistory){ $args += "--no-history" }

& $Py @args
