$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$frontendCwd = Join-Path $repoRoot "frontend"
$log = Join-Path $repoRoot "frontend_web.log"

Set-Location $frontendCwd
npm run dev -- -p 5173 > "$log" 2>&1
