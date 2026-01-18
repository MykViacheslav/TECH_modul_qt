import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# Find and replace def _rebuild_parts(...) block up to next "def _refresh_scene"
pat = re.compile(r"(?ms)^\s*def _rebuild_parts\(self\)\s*->\s*None:\s*\n.*?^\s*def _refresh_scene\(self\)\s*->\s*None:\s*\n", re.MULTILINE)

replacement = r'''    def _rebuild_parts(self) -> None:
        W = float(self.in_W.value())
        H = float(self.in_H.value())
        D = float(self.in_D.value())
        t = float(self.in_thick.value())
        bt = float(self.in_back_thick.value())

        has_L = bool(self.ck_side_left.isChecked())
        has_R = bool(self.ck_side_right.isChecked())
        has_T = bool(self.ck_top.isChecked())
        has_B = bool(self.ck_bottom.isChecked())

        front_enabled = bool(self.ck_front.isChecked())
        back_enabled = bool(self.ck_back.isChecked())
        middle_on = bool(self.ck_middle.isChecked())

        # shelves
        shelves_on = bool(self.ck_shelves.isChecked())
        shelves_cnt = int(self.in_shelves.value()) if shelves_on else 0
        split_shelves = bool(self.ck_split_shelves.isChecked())

        # materials (fallbacks for placeholder index 0)
        carcass_mat = self.cb_mat_carcass.currentText().strip()
        if self.cb_mat_carcass.currentIndex() == 0:
            carcass_mat = "Płyta wiórowa 18 mm"

        back_mat = self.cb_back_mat.currentText().strip()
        if self.cb_back_mat.currentIndex() == 0:
            back_mat = "HDF 3 mm"

        front_mat = self.cb_front_mat.currentText().strip()
        if self.cb_front_mat.currentIndex() == 0:
            front_mat = "MDF 18 mm"

        front_thick = 18.0

        innerW = W - (t if has_L else 0.0) - (t if has_R else 0.0)
        innerH = H - (t if has_T else 0.0) - (t if has_B else 0.0)
        innerW = max(0.0, innerW)
        innerH = max(0.0, innerH)

        parts: Dict[str, Part] = {}

        def ensure(key: str, name: str, a: float, b: float, thick: float, default_mat: str):
            old = self.parts.get(key)
            if old is None:
                parts[key] = Part(key, name, a, b, thick, default_mat)
            else:
                old.name_pl = name
                old.a_mm, old.b_mm = a, b
                old.thick_mm = thick
                if not old.material:
                    old.material = default_mat
                parts[key] = old

        # sides
        if has_L:
            ensure("side_left", "Bok lewy", D, H, t, carcass_mat)
        if has_R:
            ensure("side_right", "Bok prawy", D, H, t, carcass_mat)

        # top/bottom
        if has_T:
            ensure("top", "Wieniec góra", innerW, D, t, carcass_mat)
        if has_B:
            ensure("bottom", "Wieniec dół", innerW, D, t, carcass_mat)

        # back
        if back_enabled:
            ensure("back", "Plecy", W, H, bt, back_mat)

        # middle partitions (by offsets list; if empty -> one centered)
        self._middle_xs_mm = []
        if middle_on:
            raw_off = ""
            try:
                raw_off = (self.in_middle_offsets.text() or "").strip()
            except Exception:
                raw_off = ""

            offsets = []
            if raw_off:
                for tok in raw_off.replace(";", ",").split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    try:
                        offsets.append(float(tok))
                    except Exception:
                        pass

            x_min = 0.0
            x_max = max(0.0, innerW - t)

            if offsets:
                xs = [max(x_min, min(x_max, float(x))) for x in offsets]
            else:
                # single centered partition if checkbox ON and no offsets
                xs = [max(x_min, min(x_max, (innerW - t) / 2.0))]

            # dedupe
            xs2 = []
            for x in sorted(xs):
                if not xs2 or abs(x - xs2[-1]) > 0.5:
                    xs2.append(x)
            xs = xs2

            self._middle_xs_mm = xs
            for i, _x in enumerate(xs, start=1):
                ensure(f"middle_{i}", f"Środkowa ścianka {i}", D, innerH, t, carcass_mat)

        # shelves
        if shelves_cnt > 0:
            for i in range(1, shelves_cnt + 1):
                if middle_on and split_shelves:
                    a_half = max(0.0, (innerW - t) / 2.0)
                    ensure(f"shelf_{i}_L", f"Półka {i} (lewa)", a_half, D, t, carcass_mat)
                    ensure(f"shelf_{i}_R", f"Półka {i} (prawa)", a_half, D, t, carcass_mat)
                else:
                    ensure(f"shelf_{i}", f"Półka {i}", innerW, D, t, carcass_mat)

        # fronts
        if front_enabled and self.cb_front_mode.currentText() != "Brak":
            mode = self.cb_front_mode.currentText()
            n = int(self.in_front_count.value())
            gap = float(self.in_front_gap.value())
            side_off = float(self.in_front_side.value())
            hmode = self.cb_front_hmode.currentText()

            openH = H if hmode == "Na całą wysokość" else max(0.0, H - (t if has_T else 0.0) - (t if has_B else 0.0))
            if mode == "Drzwi":
                availW = max(0.0, W - 2 * side_off)
                panelW = max(0.0, (availW - gap * (n - 1)) / max(1, n))
                for i in range(1, n + 1):
                    ensure(f"front_{i}", f"Front {i}", panelW, openH, front_thick, front_mat)
            else:
                availW = max(0.0, W - 2 * side_off)
                availH = max(0.0, openH)
                panelH = max(0.0, (availH - gap * (n - 1)) / max(1, n))
                for i in range(1, n + 1):
                    ensure(f"front_{i}", f"Front szuflady {i}", availW, panelH, front_thick, front_mat)

        self.parts = parts
        if self.selected_key not in self.parts and self.parts:
            self.selected_key = next(iter(self.parts.keys()))

        self._update_drawer_nl_label()

    def _refresh_scene(self) -> None:
'''

m = pat.search(txt)
if not m:
    raise SystemExit("Could not find _rebuild_parts -> _refresh_scene block to replace. Paste surrounding code and I'll adapt the matcher.")

txt2 = pat.sub(replacement, txt, count=1)
p.write_text(txt2, encoding="utf-8")
print("OK: _rebuild_parts replaced with clean implementation")
