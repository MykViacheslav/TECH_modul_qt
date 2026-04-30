param(
  [string]$BackendUrl = "http://localhost:8000/system/summary",
  [string]$FrontendUrl = "http://localhost:3000/",
  [int]$TimeoutSec = 10,
  [int]$Retries = 6,
  [int]$RetryDelaySec = 3
)

$ErrorActionPreference = "Stop"

function Test-Url {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Timeout = 2
  )

  try {
    $resp = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $Timeout -UseBasicParsing
    return @{
      ok = $true
      code = [int]$resp.StatusCode
      url = $Url
      body = [string]$resp.Content
    }
  } catch {
    $statusCode = 0
    $body = ""
    if ($_.Exception.Response) {
      try {
        $statusCode = [int]$_.Exception.Response.StatusCode
      } catch { $statusCode = 0 }
      try {
        $sr = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
        $body = $sr.ReadToEnd()
      } catch {
        $body = ""
      }
    }
    return @{
      ok = $false
      code = $statusCode
      url = $Url
      error = $_.Exception.Message
      body = $body
    }
  }
}

$backend = Test-Url -Url $BackendUrl -Timeout $TimeoutSec
$frontend = Test-Url -Url $FrontendUrl -Timeout $TimeoutSec

for ($i = 1; $i -le $Retries; $i++) {
  $backendSignatureOk = $false
  if ($backend.ok -or $backend.code -gt 0) {
    if (($backend.body -like "*TECH-V4*") -or ($backend.body -like "*api_version*")) {
      $backendSignatureOk = $true
    }
  }

  $frontendSignatureOk = $false
  if ($frontend.ok -or $frontend.code -gt 0) {
    if (($frontend.body -like "*TECH_modul*") -or ($frontend.body -like "*Wybierz pracownika*") -or ($frontend.body -like "*Workspace*") -or ($frontend.body -like "*zamowienia*")) {
      $frontendSignatureOk = $true
    }
  }

  if (($backend.ok -and $backendSignatureOk) -and ($frontend.ok -and $frontendSignatureOk)) {
    break
  }

  Start-Sleep -Seconds $RetryDelaySec
  $backend = Test-Url -Url $BackendUrl -Timeout $TimeoutSec
  $frontend = Test-Url -Url $FrontendUrl -Timeout $TimeoutSec
}

Write-Host "SMOKE CHECK"
Write-Host "Backend:  $($backend.url)"
Write-Host "Frontend: $($frontend.url)"

if ($backend.ok) {
  Write-Host "OK backend ($($backend.code))"
} else {
  Write-Host "FAIL backend: $($backend.error) [code=$($backend.code)]"
}

if ($frontend.ok) {
  Write-Host "OK frontend ($($frontend.code))"
} else {
  Write-Host "FAIL frontend: $($frontend.error) [code=$($frontend.code)]"
}

$backendSignatureOk = $false
if ($backend.ok -or $backend.code -gt 0) {
  if (($backend.body -like "*TECH-V4*") -or ($backend.body -like "*api_version*")) {
    $backendSignatureOk = $true
  }
}

$frontendSignatureOk = $false
if ($frontend.ok -or $frontend.code -gt 0) {
  if (($frontend.body -like "*Workspace*") -or ($frontend.body -like "*workspace*") -or ($frontend.body -like "*zamowienia*") -or ($frontend.body -like "*TECH_modul*")) {
    $frontendSignatureOk = $true
  }
}

if (($backend.ok -and $backendSignatureOk) -and ($frontend.ok -and $frontendSignatureOk)) {
  Write-Host "STACK STATUS: OK"
  exit 0
}

if (-not $backendSignatureOk) {
  Write-Host "DIAGNOZA: Backend na porcie 8000 nie wyglada na API TECH_MODUL (/system/summary + TECH-V4)."
}
if (-not $frontendSignatureOk) {
  Write-Host "DIAGNOZA: Frontend na porcie 3000 nie wyglada na web TECH_MODUL (strona startowa/workspace)."
}
Write-Host "Podpowiedz:"
Write-Host "1) powershell -ExecutionPolicy Bypass -File .\scripts\start_web_stack.ps1 -KillConflictingPorts"
Write-Host "2) powershell -ExecutionPolicy Bypass -File .\scripts\check_web_stack.ps1"
Write-Host "STACK STATUS: FAIL"
exit 1
