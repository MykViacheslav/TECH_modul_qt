#!/usr/bin/env bash
set -euo pipefail

echo "[guard_patch_and_test] Starting backup and test workflow before applying patch."

# 1) Run a local backup of data before any patch
echo "[guard_patch_and_test] Creating data backup..."
python3 scripts/backup_data.py

# 2) Run tests to verify current state
echo "[guard_patch_and_test] Running test suite (no-GUI first)..."
pytest tests/test_end_to_end_no_gui.py -q
pytest tests/test_service_tabs.py -q

# Optional: if user wants to run all tests, uncomment the next line
# pytest -q

# 3) Apply patch if provided
if [ "$#" -ge 1 ]; then
  PATCH_FILE="$1"
  if [ -f "$PATCH_FILE" ]; then
    echo "[guard_patch_and_test] Applying patch: $PATCH_FILE"
    git apply "$PATCH_FILE" || { echo "Failed to apply patch: $PATCH_FILE"; exit 2; }
  else
    echo "[guard_patch_and_test] Patch file not found: $PATCH_FILE"
    exit 3
  fi
  echo "[guard_patch_and_test] Patch applied."
else
  echo "[guard_patch_and_test] No patch file provided. Ready for patch application steps."
fi

echo "[guard_patch_and_test] All steps completed."
exit 0
