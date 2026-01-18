from __future__ import annotations
from pathlib import Path
import re

p = Path(r"C:\\PythonProject\\TECH_modul\\TECH_modul_qt\\src\\tabs\\module_widget\.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# 1) remove broken v14/v15 injections from _on_recalc (they reference tables/lines that don't exist)
txt = re.sub(r'(?ms)^\s*# FRONT BOM v14.*?^\s*pass\s*$', '', txt)
txt = re.sub(r'(?ms)^\s*# FRONT BOM v15.*?^\s*pass\s*$', '', txt)

# 2) split BOM material areas into carcass/rest vs fronts
pattern = r'(?ms)mats_m2:\s*Dict\[str,\s*float\]\s*=\s*\{\}\s*\n\s*def\s+add_area\(mat:\s*str,\s*a:\s*float,\s*b:\s*float\):\s*\n.*?\n\s*part_list\s*=\s*list\(self\.parts\.values\(\)\)\s*\n\s*self\.lbl_parts\.setText\(f"parts:\s*\{len\(part_list\)\}"\)\s*\n\s*for\s+p\s+in\s+part_list:\s*\n\s*add_area\(p\.material\s+or\s+"—",\s*p\.a_mm,\s*p\.b_mm\)\s*\n'

replacement = (
"mats_m2: Dict[str, float] = {}          # korpus / reszta\n"
"mats_front_m2: Dict[str, float] = {}    # fronty osobno\n"
"\n"
"def add_area(dst: Dict[str, float], mat: str, a: float, b: float):\n"
"    if not mat:\n"
"        mat = \"—\"\n"
"    dst[mat] = dst.get(mat, 0.0) + mm2_to_m2(a * b)\n"
"\n"
"part_list = list(self.parts.values())\n"
"self.lbl_parts.setText(f\"parts: {len(part_list)}\")\n"
"\n"
"for p in part_list:\n"
"    if p.key.startswith(\"front_\"):\n"
"        add_area(mats_front_m2, p.material or \"—\", p.a_mm, p.b_mm)\n"
"    else:\n"
"        add_area(mats_m2, p.material or \"—\", p.a_mm, p.b_mm)\n"
)

new_txt, n = re.subn(pattern, replacement, txt)
if n == 0:
    raise SystemExit(
        "ERROR: Nie znalazłem bloku do podmiany w _refresh_bom(). "
        "Najpewniej różni się format. Wklej mi fragment _refresh_bom od 'mats_m2' do pętli 'for p in part_list'."
    )

# 3) rename section and add FRONTY section after it
old_block = (
'lines.append("MATERIAŁY (m²):")\n'
'        for k in sorted(mats_m2.keys()):\n'
'            lines.append(f"- {k}: {mats_m2[k] * qty:.3f} m²")\n'
'        lines.append("")\n'
)

new_block = (
'lines.append("MATERIAŁY KORPUS (m²):")\n'
'        for k in sorted(mats_m2.keys()):\n'
'            lines.append(f"- {k}: {mats_m2[k] * qty:.3f} m²")\n'
'        lines.append("")\n'
'\n'
'        if mats_front_m2:\n'
'            lines.append("FRONTY (m²):")\n'
'            for k in sorted(mats_front_m2.keys()):\n'
'                lines.append(f"- {k}: {mats_front_m2[k] * qty:.3f} m²")\n'
'            lines.append("")\n'
)

if old_block not in new_txt:
    # maybe already changed earlier - try a softer replace of just the header
    if 'lines.append("MATERIAŁY (m²):")' in new_txt:
        new_txt = new_txt.replace('lines.append("MATERIAŁY (m²):")', 'lines.append("MATERIAŁY KORPUS (m²):")')
        # insert FRONTY section right after the "lines.append("")" that ends the materials section
        # best-effort: after first occurrence of that empty line append following the materials loop
        marker = 'lines.append("MATERIAŁY KORPUS (m²):")'
        pos = new_txt.find(marker)
        if pos != -1:
            # find the next occurrence of 'lines.append("")' after that
            pos2 = new_txt.find('lines.append("")', pos)
            if pos2 != -1:
                pos3 = new_txt.find("\n", pos2)  # end of that line
                insert = (
                    '\n'
                    '        if mats_front_m2:\n'
                    '            lines.append("FRONTY (m²):")\n'
                    '            for k in sorted(mats_front_m2.keys()):\n'
                    '                lines.append(f"- {k}: {mats_front_m2[k] * qty:.3f} m²")\n'
                    '            lines.append("")\n'
                )
                new_txt = new_txt[:pos3+1] + insert + new_txt[pos3+1:]
    else:
        raise SystemExit("ERROR: Nie znalazłem bloku 'MATERIAŁY (m²)' do podmiany. Podeślij kawałek _refresh_bom().")
else:
    new_txt = new_txt.replace(old_block, new_block)

p.write_text(new_txt, encoding="utf-8")
print("OK: BOM rozdzielony -> MATERIAŁY KORPUS + FRONTY. Usunięto też wklejki v14/v15 z _on_recalc.")

