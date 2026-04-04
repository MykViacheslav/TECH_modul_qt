<#
PowerShell guard script equivalent to Bash guard_patch_and_test.sh
Usage: powershell -File scripts/guard_patch_and_test.ps1 [-PatchPath <path-to-patch.diff>]
This script:
- Creates a data backup via scripts/backup_data.py
- Runs a no-GUI and service tab tests
- Optionally applies a patch if PatchPath is provided
#>
param(
  [string]$PatchPath = $null
)

Write-Host "[guard_patch_and_test] Starting backup and test workflow before applying patch."

# 1) Run a local backup of data before any patch
Write-Host "[guard_patch_and_test] Creating data backup..."
python scripts/backup_data.py

# 2) Run tests to verify current state
Write-Host "[guard_patch_and_test] Running test suite (no-GUI first)..."
python -m pytest tests/test_end_to_end_no_gui.py -q
python -m pytest tests/test_service_tabs.py -q

if ($PatchPath -and (Test-Path $PatchPath)) {
  Write-Host "[guard_patch_and_test] Applying patch: $PatchPath"
  git apply "$PatchPath" 2>&1 | Write-Host
} elseif ($PatchPath) {
  Write-Host "[guard_patch_and_test] Patch file not found: $PatchPath"; exit 3
}

Write-Host "[guard_patch_and_test] Completed."
