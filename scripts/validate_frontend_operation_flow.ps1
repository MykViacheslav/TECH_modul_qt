param(
  [string]$BaseUrl = "http://localhost:8000",
  [int]$ProjectId = 1
)

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Error $msg
  exit 1
}

Write-Host "[1/4] Pobieram moduły projektu..."
$mods = Invoke-RestMethod -Method Get -Uri "$BaseUrl/config/modules/$ProjectId"
if (-not $mods -or $mods.Count -lt 1) {
  Fail "Brak modułów do testu."
}
$first = $mods[0]
$moduleId = [string]$first.id
$beforeDepth = [int]$first.depth
$targetDepth = $beforeDepth + 10

Write-Host "[2/4] Preview operation dla modułu id=$moduleId..."
$previewBody = @{
  action = "module.set_depth"
  target = @{ id = $moduleId }
  params = @{ depth_mm = $targetDepth }
  source = "flow_check"
} | ConvertTo-Json -Depth 8

$preview = Invoke-RestMethod -Method Post -ContentType "application/json" -Uri "$BaseUrl/operations/module/preview" -Body $previewBody
if ($preview.status -ne "ok" -or -not $preview.can_apply) {
  Fail "Preview nieudany: status=$($preview.status)"
}

Write-Host "[3/4] Apply operation..."
$applyBody = @{
  action = "module.set_depth"
  target = @{ id = $moduleId }
  params = @{ depth_mm = $targetDepth }
  source = "flow_check"
} | ConvertTo-Json -Depth 8

$apply = Invoke-RestMethod -Method Post -ContentType "application/json" -Uri "$BaseUrl/operations/module/apply" -Body $applyBody
if ($apply.status -ne "ok") {
  Fail "Apply nieudany: status=$($apply.status)"
}

Write-Host "[4/4] Weryfikuję odświeżony stan z backend..."
$modsAfter = Invoke-RestMethod -Method Get -Uri "$BaseUrl/config/modules/$ProjectId"
$same = $modsAfter | Where-Object { [string]$_.id -eq $moduleId } | Select-Object -First 1
if (-not $same) {
  Fail "Nie znaleziono modułu po apply."
}
if ([int]$same.depth -ne $targetDepth) {
  Fail "Niezgodna głębokość po apply. Oczekiwano $targetDepth, jest $($same.depth)."
}

Write-Host "OK: preview/apply/reload działają poprawnie dla module.set_depth." -ForegroundColor Green
