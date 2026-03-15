param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".git")) {
    git init
}

git branch -M $Branch

if (-not (git config user.name)) {
    Write-Host "Brak git user.name. Ustaw go poleceniem:"
    Write-Host 'git config --global user.name "Twoje Imie"'
    exit 1
}

if (-not (git config user.email)) {
    Write-Host "Brak git user.email. Ustaw go poleceniem:"
    Write-Host 'git config --global user.email "twoj@email.pl"'
    exit 1
}

$hasOrigin = $false
try {
    $null = git remote get-url origin
    $hasOrigin = $true
}
catch {
    $hasOrigin = $false
}

if (-not $hasOrigin) {
    git remote add origin $RepoUrl
}

git add .
git commit -m "Initial private backup of TECH_modul" 2>$null
git push -u origin $Branch
