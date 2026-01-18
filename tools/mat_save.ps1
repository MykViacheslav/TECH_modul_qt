param(
  [Parameter(Mandatory=$true)][string]$Code,
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Kind = "board",
  [double]$Thickness = 0,
  [string]$Note = "",
  [switch]$Overwrite,
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)
. (Join-Path $PSScriptRoot "env.ps1")
$Root = Split-Path $PSScriptRoot -Parent
$Cli  = Join-Path $Root "src\tools\material_db_cli.py"

$args = @($Cli,"--db",$DbPath,"save","--code",$Code,"--name",$Name,"--kind",$Kind)
if($Thickness -gt 0){ $args += @("--thickness",$Thickness) }
if($Note -and $Note.Trim().Length -gt 0){ $args += @("--note",$Note) }
if($Overwrite){ $args += "--overwrite" }

& $Py @args
