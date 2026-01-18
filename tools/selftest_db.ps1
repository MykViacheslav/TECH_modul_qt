param(
  [string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "data\tech.db")
)
$ErrorActionPreference="Stop"

Write-Host "== SELFTEST_DB =="

.\tools\mod_init.ps1
.\tools\mat_init.ps1

# base materials
.\tools\mat_save.ps1 -Anchor MDF18 -Kind board -Name "MDF 18mm" -Thickness 18 -Overwrite
.\tools\mat_save.ps1 -Anchor HPL08 -Kind hpl   -Name "HPL 0.8mm" -Thickness 0.8 -Overwrite

# composite: MDF18 + HPL0.8 front+back => 19.6 (auto from layers)
$payload = '{ "layers": [
  {"material":"MDF18","thickness_mm":18.0,"side":"core"},
  {"material":"HPL08","thickness_mm":0.8,"side":"front"},
  {"material":"HPL08","thickness_mm":0.8,"side":"back"}
]}'
.\tools\mat_save.ps1 -Anchor MDF18_HPL08_2S -Kind composite -Name "MDF18 + HPL0.8 2S" -PayloadJson $payload -Overwrite

# module save (na razie materials jako string; potem zrobimy material_anchor)
.\tools\mod_save.ps1 -Anchor M01 -Name "Baza M01" -Width 600 -Height 720 -Depth 560 -Materials "MDF18_HPL08_2S" -Overwrite

Write-Host "--- mat_get MDF18_HPL08_2S ---"
.\tools\mat_get.ps1 -Anchor MDF18_HPL08_2S | Out-Host

Write-Host "--- mod_get M01 ---"
.\tools\mod_get.ps1 -Anchor M01 | Out-Host

Write-Host "--- mat_list (5) ---"
.\tools\mat_list.ps1 -Limit 5 | Out-Host

Write-Host "--- mod_list (5) ---"
.\tools\mod_list.ps1 -Limit 5 | Out-Host

Write-Host "SELFTEST_OK"
