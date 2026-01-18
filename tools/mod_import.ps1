param(
  [Parameter(Mandatory=$true)][string]$Path,
  [switch]$Overwrite,
  [switch]$NoHistory,
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)

. (Join-Path $PSScriptRoot "env.ps1")

$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\module_db_cli.py"

$args = @($Cli, "--db", $DbPath, "import", "--path", $Path)
if($Overwrite){ $args += "--overwrite" }
if($NoHistory){ $args += "--no-history" }

& $Py @args
