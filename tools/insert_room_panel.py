"""
Inserts _compute_room_metrics / _refresh_room_panel / _detect_collisions /
_refresh_collisions methods into tab_sciana_layout.py
"""
import sys

path = "C:/PythonProject/TECH_modul/src/tabs/sciana/tab_sciana_layout.py"

with open(path, "rb") as f:
    data = f.read()

insert_before = b"    def _refresh_summary(self) -> None:"

new_methods = r"""    # =====================================================================
    # PANEL POMIESZCZENIA + KOLIZJE
    # =====================================================================

    def _compute_room_metrics(self) -> dict:
        w = self._wall
        wall_a = max(1.0, float(w.wall_a_width_mm or 4000))
        wall_b = max(1.0, float(w.wall_b_width_mm or 2600))
        wall_c = max(1.0, float(w.wall_c_width_mm or 2600))
        room_h = max(1.0, float(w.room_height_mm or 2600))
        base_depth = max(1.0, float(w.base_depth_mm or 600))
        plinth = max(0.0, float(w.base_plinth_mm or 0))
        upper_cl = max(0.0, float(w.upper_clearance_mm or 0))
        top_off = max(0.0, float(w.top_offset_mm or 0))
        bot_off = max(0.0, float(w.bottom_offset_mm or 0))
        left_off_base = max(0.0, float(w.base_offset_left_mm or 0))
        right_off_base = max(0.0, float(w.base_offset_right_mm or 0))
        left_off_upper = max(0.0, float(w.upper_offset_left_mm or 0))
        right_off_upper = max(0.0, float(w.upper_offset_right_mm or 0))
        layout = str(w.layout_type or "line")
        base_zone_h = max(0.0, room_h - plinth - upper_cl - top_off - bot_off)
        total_wall_mm = wall_a
        if layout in ("l", "c"):
            total_wall_mm += wall_b
        if layout == "c":
            total_wall_mm += wall_c
        base_avail_w = max(0.0, wall_a - left_off_base - right_off_base)
        upper_avail_w = max(0.0, wall_a - left_off_upper - right_off_upper)
        area_a_m2 = wall_a * room_h / 1_000_000
        obstacles = list(w.obstacles or [])
        obs_count = len(obstacles)
        obs_area_m2 = sum(
            float(getattr(o, "width_mm", 0) or 0) * float(getattr(o, "height_mm", 0) or 0)
            for o in obstacles
        ) / 1_000_000
        fill_pct = (obs_area_m2 / area_a_m2 * 100.0) if area_a_m2 > 0 else 0.0
        return {
            "wall_a": wall_a, "wall_b": wall_b, "wall_c": wall_c,
            "room_h": room_h, "base_depth": base_depth, "plinth": plinth,
            "upper_cl": upper_cl, "top_off": top_off, "bot_off": bot_off,
            "base_zone_h": base_zone_h, "layout": layout,
            "total_wall_mm": total_wall_mm,
            "base_avail_w": base_avail_w, "upper_avail_w": upper_avail_w,
            "area_a_m2": area_a_m2,
            "obs_count": obs_count, "obs_area_m2": obs_area_m2,
            "fill_pct": fill_pct,
        }

    def _refresh_room_panel(self) -> None:
        if not hasattr(self, "lab_room_info"):
            return
        m = self._compute_room_metrics()
        layout_label = {"line": "Prosta", "l": "L", "c": "C"}.get(m["layout"], m["layout"])
        lines = [f"Uklad: {layout_label}", f"Sciana A: {m['wall_a']:.0f} mm"]
        if m["layout"] in ("l", "c"):
            lines.append(f"Sciana B: {m['wall_b']:.0f} mm")
        if m["layout"] == "c":
            lines.append(f"Sciana C: {m['wall_c']:.0f} mm")
        lines += [
            f"Lacznie scian: {m['total_wall_mm']:.0f} mm",
            f"Wysokosc pomieszczenia: {m['room_h']:.0f} mm",
            f"Glebokosc zabudowy: {m['base_depth']:.0f} mm",
            "",
            f"Cokol: {m['plinth']:.0f} mm",
            f"Gorny odstep: {m['upper_cl']:.0f} mm",
            f"Strefa zabudowy (wys.): {m['base_zone_h']:.0f} mm",
            f"Szerokosc dolnej zabudowy: {m['base_avail_w']:.0f} mm",
            f"Szerokosc gornej zabudowy: {m['upper_avail_w']:.0f} mm",
            "",
            f"Powierzchnia sciany A: {m['area_a_m2']:.2f} m2",
            f"Przeszkody ({m['obs_count']}): {m['obs_area_m2']:.2f} m2",
            f"Wypelnienie: {m['fill_pct']:.1f}%",
        ]
        self.lab_room_info.setText("\n".join(lines))

    def _detect_collisions(self) -> list[str]:
        warnings: list[str] = []
        obstacles = list(self._wall.obstacles or [])
        room_h = max(1.0, float(self._wall.room_height_mm or 2600))
        wall_a = max(1.0, float(self._wall.wall_a_width_mm or 4000))
        plinth = max(0.0, float(self._wall.base_plinth_mm or 0))
        # -- 1. Nakładanie przeszkod na tej samej scianie --
        by_side: dict[str, list] = {}
        for obs in obstacles:
            side = str(getattr(obs, "wall_side", "A") or "A").strip().upper()
            by_side.setdefault(side, []).append(obs)
        for side, obs_list in by_side.items():
            for i, a in enumerate(obs_list):
                ax1 = float(getattr(a, "x_mm", 0) or 0)
                ax2 = ax1 + max(0.0, float(getattr(a, "width_mm", 0) or 0))
                ay1 = float(getattr(a, "y_mm", 0) or 0)
                ay2 = ay1 + max(0.0, float(getattr(a, "height_mm", 0) or 0))
                for j, b in enumerate(obs_list):
                    if j <= i:
                        continue
                    bx1 = float(getattr(b, "x_mm", 0) or 0)
                    bx2 = bx1 + max(0.0, float(getattr(b, "width_mm", 0) or 0))
                    by1 = float(getattr(b, "y_mm", 0) or 0)
                    by2 = by1 + max(0.0, float(getattr(b, "height_mm", 0) or 0))
                    if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                        na = str(getattr(a, "name", "") or f"#{i+1}").strip() or f"#{i+1}"
                        nb = str(getattr(b, "name", "") or f"#{j+1}").strip() or f"#{j+1}"
                        warnings.append(f"[{side}] Nakladanie: {na} <-> {nb}")
        # -- 2. Przeszkody poza granicami sciany --
        for obs in obstacles:
            side = str(getattr(obs, "wall_side", "A") or "A").strip().upper()
            x1 = float(getattr(obs, "x_mm", 0) or 0)
            x2 = x1 + max(0.0, float(getattr(obs, "width_mm", 0) or 0))
            y1 = float(getattr(obs, "y_mm", 0) or 0)
            y2 = y1 + max(0.0, float(getattr(obs, "height_mm", 0) or 0))
            name = str(getattr(obs, "name", "") or getattr(obs, "kind", "?")).strip() or "?"
            if side == "A" and x2 > wall_a:
                warnings.append(f"[A] {name}: wystaje poza sciane o {x2 - wall_a:.0f} mm")
            if y2 > room_h:
                warnings.append(f"[{side}] {name}: wykracza poza sufit o {y2 - room_h:.0f} mm")
            if y1 < 0:
                warnings.append(f"[{side}] {name}: y < 0 (ponizej podlogi)")
        # -- 3. Przeszkody techniczne w strefie cokolu --
        technical = {"pipe", "socket", "plumbing"}
        for obs in obstacles:
            kind = str(getattr(obs, "kind", "") or "").strip()
            if kind not in technical:
                continue
            name = str(getattr(obs, "name", "") or kind).strip() or kind
            y1 = float(getattr(obs, "y_mm", 0) or 0)
            y2 = y1 + max(0.0, float(getattr(obs, "height_mm", 0) or 0))
            if plinth > 0 and y1 < plinth:
                warnings.append(f"{name}: srodek w strefie cokolu ({plinth:.0f} mm)")
        return warnings

    def _refresh_collisions(self) -> None:
        if not hasattr(self, "lab_collisions"):
            return
        warnings = self._detect_collisions()
        if not warnings:
            self.lab_collisions.setStyleSheet(
                "font-size:11px; color:#15803d; font-weight:600;"
            )
            self.lab_collisions.setText("Brak kolizji")
        else:
            self.lab_collisions.setStyleSheet(
                "font-size:11px; color:#b91c1c; font-weight:600;"
            )
            self.lab_collisions.setText("\n".join(f"[!] {w}" for w in warnings))

""".encode("utf-8")

idx = data.find(insert_before)
if idx < 0:
    print("NOT FOUND - insert_before marker missing")
    sys.exit(1)

new_data = data[:idx] + new_methods + data[idx:]
with open(path, "wb") as f:
    f.write(new_data)
print(f"OK - inserted {len(new_methods)} bytes before _refresh_summary")
