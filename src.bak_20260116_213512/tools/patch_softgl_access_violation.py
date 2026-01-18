from __future__ import annotations
from pathlib import Path
import re

proj = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt""")
run_path = proj / "src" / "app" / "run_tabs_min.py"
mod_path = proj / "src" / "tabs" / "module_widget.py"

# ---------------------------
# 1) Patch run_tabs_min.py (force software OpenGL before QApplication)
# ---------------------------
run_txt = run_path.read_text(encoding="utf-8", errors="ignore")
if "AA_UseSoftwareOpenGL" not in run_txt:
    # insert right after "from PySide6 import QtWidgets"
    run_txt2 = re.sub(
        r"(?m)^(from\s+PySide6\s+import\s+QtWidgets\s*)$",
        r"\1\nfrom PySide6 import QtCore\n\n# HOTFIX: Software OpenGL (avoid GPU driver crashes)\nQtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)\n",
        run_txt,
        count=1
    )
    if run_txt2 == run_txt:
        # fallback: insert near top after imports
        run_txt2 = run_txt.replace(
            "import sys\n",
            "import sys\nfrom PySide6 import QtCore\n\n# HOTFIX: Software OpenGL (avoid GPU driver crashes)\nQtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)\n\n"
        )
    run_path.write_text(run_txt2, encoding="utf-8")
    print("OK: patched run_tabs_min.py (AA_UseSoftwareOpenGL)")
else:
    print("SKIP: run_tabs_min.py already has AA_UseSoftwareOpenGL")

# ---------------------------
# 2) Patch module_widget.py: disable QOpenGLWidget viewport if used
# ---------------------------
mod_txt = mod_path.read_text(encoding="utf-8", errors="ignore")

changed = 0

# if there is setViewport(QOpenGLWidget()), replace with QWidget() (safe)
pat = r"(?m)^(?P<indent>\s*)self\.view\.setViewport\(\s*.*QOpenGLWidget\s*\(\s*\)\s*\)\s*$"
def repl(m):
    ind = m.group("indent")
    return (
        ind + "# HOTFIX: disable QOpenGLWidget viewport (avoid access violation)\n" +
        ind + "self.view.setViewport(QtWidgets.QWidget())"
    )
mod_txt2, n = re.subn(pat, repl, mod_txt)
changed += n

# also handle "setViewport(QtOpenGLWidgets.QOpenGLWidget())"
pat2 = r"(?m)^(?P<indent>\s*)self\.view\.setViewport\(\s*QtOpenGLWidgets\..*QOpenGLWidget\s*\(\s*\)\s*\)\s*$"
mod_txt2, n2 = re.subn(pat2, repl, mod_txt2)
changed += n2

# ensure QtWidgets imported (module_widget likely already has it; if not, add minimal)
if changed and "from PySide6.QtWidgets" not in mod_txt2 and "QtWidgets" not in mod_txt2:
    mod_txt2 = "from PySide6 import QtWidgets\n" + mod_txt2

if changed:
    mod_path.write_text(mod_txt2, encoding="utf-8")
    print(f"OK: patched module_widget.py (replaced setViewport(QOpenGLWidget) x{changed})")
else:
    print("SKIP: module_widget.py has no setViewport(QOpenGLWidget) to patch (still OK)")

print("DONE.")
