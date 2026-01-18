$ErrorActionPreference="Stop"
$Proj = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
Set-Location $Proj

$Handoff = Join-Path $Proj "_handoff"
if(-not (Test-Path $Handoff)){ New-Item -ItemType Directory -Path $Handoff | Out-Null }

$Venv = Join-Path $Proj ".venv"
$Py   = Join-Path $Venv "Scripts\python.exe"
$Pip  = Join-Path $Venv "Scripts\pip.exe"
if(-not (Test-Path $Py)){ python -m venv .venv }

try { & $Py -c "import PySide6" | Out-Null } catch { & $Pip install PySide6 | Out-Host }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Src   = Join-Path $Proj "src"
$test  = Join-Path $Handoff ("selftest_" + $stamp + ".py")
$log   = Join-Path $Handoff ("selftest_" + $stamp + ".txt")

@"
import os, sys, traceback

SRC = r"$Src"
sys.path.insert(0, SRC)

# QApplication first
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

def fail(msg):
    print("SELFTEST_FAIL:", msg)
    sys.exit(1)

print("SRC:", SRC)
print("PY:", sys.executable)

# 1) compileall
import compileall
ok = compileall.compile_dir(SRC, quiet=1)
print("compileall:", ok)
if not ok:
    fail("compileall failed")

# 2) tabs registry check
from tabs.registry import build_tabs
tabs = build_tabs(None)
print("\\nTabs from registry:")
mod_ok = False
for title, w in tabs:
    cls = w.__class__.__module__ + "." + w.__class__.__name__
    print(" -", title, "=>", cls)
    if "Modu" in title or "Moduł" in title:
        # must NOT be tab_module_web
        if "tab_module_web" in cls:
            fail("Moduł points to tab_module_web (web placeholder)")
        if "tab_module" in cls:
            mod_ok = True

if not mod_ok:
    print("WARN: could not positively confirm tab_module in registry (check title encoding).")

# 3) instantiate Tab(Moduł) and ensure it has content
from tabs.tab_module import Tab
t = Tab(None)
lay = t.layout()
cnt = lay.count() if lay else 0
print("\\nTab(Moduł) layout items:", cnt)
if cnt <= 0:
    fail("Tab(Moduł) has empty layout")

print("SELFTEST_OK")
"@ | Set-Content -LiteralPath $test -Encoding UTF8

if(Test-Path $log){ Remove-Item $log -Force }

# run unbuffered to always get log
& $Py -u $test *>> $log

Write-Host "✅ Selftest log:"
Write-Host $log
Write-Host "---- tail ----"
Get-Content $log -Tail 120 | Out-Host
