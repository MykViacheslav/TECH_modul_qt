import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# 1) import ProjectTreeWidget (add after existing imports)
if "from widgets.project_tree import ProjectTreeWidget" not in txt:
    # put it near other widget imports
    anchor = "from widgets.collapsible import CollapsibleSection"
    if anchor in txt:
        txt = txt.replace(anchor, anchor + "\nfrom widgets.project_tree import ProjectTreeWidget\n")
    else:
        # fallback: add after PySide6 imports
        m = re.search(r"from PySide6.*?\n\n", txt, flags=re.S)
        if not m:
            raise SystemExit("Cannot find place to insert import")
        pos = m.end()
        txt = txt[:pos] + "from widgets.project_tree import ProjectTreeWidget\n\n" + txt[pos:]

# 2) In _build_ui: replace right panel bottom area (gb_bom add) with a tab widget
# We look for:
# rightL.addWidget(gb_quick)
# rightL.addWidget(gb_bom, 1)
pattern = re.compile(
    r"(?ms)"
    r"(rightL\.addWidget\(gb_quick\)\s*\n)"
    r"(rightL\.addWidget\(gb_bom,\s*1\)\s*\n)"
)

if not pattern.search(txt):
    raise SystemExit("Patch failed: cannot find rightL.addWidget(gb_quick)/gb_bom block.")

replacement = (
    r"\1"
    "        # Tabs: BOM + Drzewo projektu\n"
    "        self.right_tabs = QtWidgets.QTabWidget()\n"
    "        self.right_tabs.setDocumentMode(True)\n"
    "        self.right_tabs.setMovable(False)\n"
    "        self.right_tabs.setTabsClosable(False)\n"
    "\n"
    "        # TAB 1: BOM\n"
    "        self.right_tabs.addTab(gb_bom, 'BOM')\n"
    "\n"
    "        # TAB 2: Drzewo projektu\n"
    "        self.project_tree = ProjectTreeWidget()\n"
    "        self.project_tree.partSelected.connect(self._select_part)\n"
    "        self.right_tabs.addTab(self.project_tree, 'Drzewo')\n"
    "\n"
    "        rightL.addWidget(self.right_tabs, 1)\n"
)

txt = pattern.sub(replacement, txt, count=1)

# 3) Add _refresh_tree method (near _refresh_bom or after it)
if "def _refresh_tree" not in txt:
    insert_after = "def _refresh_bom(self) -> None:"
    idx = txt.find(insert_after)
    if idx < 0:
        raise SystemExit("Cannot find _refresh_bom to anchor _refresh_tree insertion")

    # find end of _refresh_bom by scanning next 'def ' at same indent
    m = re.search(r"(?ms)^    def _refresh_bom\(self\) -> None:\n.*?(?=^    def |\Z)", txt)
    if not m:
        raise SystemExit("Cannot locate full _refresh_bom block")
    bom_block = m.group(0)

    refresh_tree = r"""

    def _refresh_tree(self) -> None:
        # best-effort: update project tree if present
        tree = getattr(self, "project_tree", None)
        if tree is None:
            return

        name = self.in_name.text().strip() if hasattr(self, "in_name") else ""
        W = float(self.in_W.value()) if hasattr(self, "in_W") else 0.0
        H = float(self.in_H.value()) if hasattr(self, "in_H") else 0.0
        D = float(self.in_D.value()) if hasattr(self, "in_D") else 0.0
        qty = int(self.in_qty.value()) if hasattr(self, "in_qty") else 1

        # adapt Part -> TreePart
        parts = {}
        for k, p in (self.parts or {}).items():
            try:
                parts[k] = dict(
                    key=p.key,
                    name_pl=p.name_pl,
                    a_mm=float(p.a_mm),
                    b_mm=float(p.b_mm),
                    thick_mm=float(p.thick_mm),
                    material=str(getattr(p, "material", "") or ""),
                )
            except Exception:
                continue

        # ProjectTreeWidget expects TreePart-like objects; it also accepts dicts with same keys in our implementation usage
        from widgets.project_tree import TreePart
        parts2 = {k: TreePart(**v) for k, v in parts.items()}

        tree.set_module(name=name, W=W, H=H, D=D, qty=qty, parts=parts2)
        try:
            tree.select_key(getattr(self, "selected_key", ""))
        except Exception:
            pass
"""
    txt = txt.replace(bom_block, bom_block + refresh_tree)

# 4) Call _refresh_tree() in _on_recalc (after _refresh_bom)
m_on = re.search(r"(?ms)^    def _on_recalc\(self\) -> None:\n.*?(?=^    def |\Z)", txt)
if not m_on:
    raise SystemExit("Cannot find _on_recalc block")

on_block = m_on.group(0)
if "self._refresh_tree()" not in on_block:
    # insert after self._refresh_bom()
    on_block2 = re.sub(
        r"(self\._refresh_bom\(\)\s*\n)",
        r"\1        self._refresh_tree()\n",
        on_block,
        count=1
    )
    txt = txt.replace(on_block, on_block2)

# 5) Sync scene selection -> tree selection (inside _select_part)
m_sel = re.search(r"(?ms)^    def _select_part\(self, key: str\) -> None:\n.*?(?=^    def |\Z)", txt)
if not m_sel:
    raise SystemExit("Cannot find _select_part block")

sel_block = m_sel.group(0)
if "project_tree" not in sel_block:
    inject = "        self._refresh_quick_panel()\n"
    if inject in sel_block:
        sel_block2 = sel_block.replace(
            inject,
            inject + "        # sync tree selection\n        try:\n            t = getattr(self, 'project_tree', None)\n            if t is not None:\n                t.select_key(key)\n        except Exception:\n            pass\n"
        )
        txt = txt.replace(sel_block, sel_block2)

p.write_text(txt, encoding="utf-8")
print("OK: added Project Tree tab (minimal impact)")
