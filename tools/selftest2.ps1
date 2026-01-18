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
$test  = Join-Path $Handoff ("selftest2_" + $stamp + ".py")
$log   = Join-Path $Handoff ("selftest2_" + $stamp + ".txt")

@"
import os, sys, traceback
SRC = r"$Src"
sys.path.insert(0, SRC)

# QApplication first (important!)
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

def fail(msg):
    print("SELFTEST_FAIL:", msg)
    raise SystemExit(1)

print("SRC:", SRC)
print("PY:", sys.executable)

import compileall
ok = compileall.compile_dir(SRC, quiet=1)
print("compileall:", ok)
if not ok:
    fail("compileall failed")

from tabs.registry import build_tabs
tabs = build_tabs(None)

print("\\nTabs from registry:")
mod_cls = None
for title, w in tabs:
    cls = w.__class__.__module__ + "." + w.__class__.__name__
    print(" -", title, "=>", cls)
    if "Modu" in title:
        mod_cls = cls

if mod_cls and "tab_module_web" in mod_cls:
    fail("Moduł points to tab_module_web (web placeholder)")

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
& $Py -u $test *>> $log

Write-Host "✅ Selftest2 log:" $log
Get-Content $log -Tail 140 | Out-Host
