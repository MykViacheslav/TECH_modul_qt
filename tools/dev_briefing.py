"""
Codzienny briefing deweloperski — TECH_modul
Uruchamia się rano, analizuje stan projektu i wypisuje plan dnia.

Użycie:
    python tools/dev_briefing.py

Automatycznie (Windows Task Scheduler):
    python C:\PythonProject\TECH_modul\tools\dev_briefing.py > briefing.txt
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PLAN_FILE = ROOT / "PLAN_ETAPOW.txt"
OUTPUT_FILE = ROOT / "briefing.txt"

_DAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
_MONTHS_PL = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]

# ── Pomocnicze ────────────────────────────────────────────────────────────────

def _today() -> str:
    d = date.today()
    return f"{_DAYS_PL[d.weekday()]}, {d.day} {_MONTHS_PL[d.month - 1]} {d.year}"


def _git_log(days: int = 3) -> str:
    since = (date.today() - timedelta(days=days)).isoformat()
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--since={since}", "--oneline", "--no-merges"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().splitlines()
        return "\n".join(f"  {l}" for l in lines) if lines else "  (brak commitów)"
    except Exception as e:
        return f"  (błąd git: {e})"


def _scan_todos(max_items: int = 15) -> list[tuple[str, int, str]]:
    """Zwraca listę (plik_rel, linia, treść) dla TODO/FIXME w src/."""
    hits: list[tuple[str, int, str]] = []
    pattern = re.compile(r"#\s*(TODO|FIXME)[:\s]+(.*)", re.IGNORECASE)
    for py_file in sorted(SRC.rglob("*.py")):
        try:
            for i, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                m = pattern.search(line)
                if m:
                    rel = py_file.relative_to(ROOT)
                    hits.append((str(rel), i, m.group(0).strip()))
                    if len(hits) >= max_items:
                        return hits
        except Exception:
            continue
    return hits


def _parse_etapy() -> list[tuple[str, str, list[str]]]:
    """
    Parsuje PLAN_ETAPOW.txt i zwraca listę
    (nagłówek_etapu, status, [bullet points]).
    Tylko IN PROGRESS i TODO.
    """
    if not PLAN_FILE.exists():
        return []

    text = PLAN_FILE.read_text(encoding="utf-8", errors="replace")
    etapy: list[tuple[str, str, list[str]]] = []

    # Znajdź sekcje zaczynające się od "ETAP" lub "Etap"
    sections = re.split(r"(?=^(?:ETAP|Etap)\s)", text, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().splitlines()
        if not lines:
            continue

        header = lines[0].strip()

        # Szukaj linii "Status:"
        status = ""
        bullets: list[str] = []
        for line in lines[1:]:
            line_s = line.strip()
            if line_s.startswith("Status:"):
                status = line_s.replace("Status:", "").strip()
            elif re.match(r"\[(?:TODO|IN PROGRESS)\]", line_s):
                bullets.append(line_s)

        if not status:
            # fallback: szukaj [IN PROGRESS] / [TODO] w nagłówku
            if "[IN PROGRESS]" in header:
                status = "[IN PROGRESS]"
            elif "[TODO]" in header:
                status = "[TODO]"

        if "[IN PROGRESS]" in status or "[TODO]" in status:
            etapy.append((header, status, bullets[:5]))

    return etapy


def _count_orders() -> int:
    import json
    path = ROOT / "data" / "orders.json"
    if not path.exists():
        path = ROOT / "orders.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, dict) else 0
    except Exception:
        return 0


# ── Generowanie briefingu ─────────────────────────────────────────────────────

def generate() -> str:
    lines: list[str] = []

    def h(text: str) -> None:
        lines.append("")
        lines.append("=" * 56)
        lines.append(f"  {text}")
        lines.append("=" * 56)

    def sub(text: str) -> None:
        lines.append(f"\n── {text} ──")

    def bullet(text: str) -> None:
        lines.append(f"  • {text}")

    def info(text: str) -> None:
        lines.append(f"  {text}")

    # Nagłówek
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════╗")
    lines.append(f"║  BRIEFING DEWELOPERSKI — TECH_modul")
    lines.append(f"║  {_today()}")
    lines.append("╚══════════════════════════════════════════════════════╝")

    # ── 1. Ostatnie commity ──────────────────────────────────────
    h("1. OSTATNIE COMMITY (3 DNI)")
    git_out = _git_log(3)
    lines.append(git_out)

    # ── 2. Aktywne etapy ────────────────────────────────────────
    h("2. AKTYWNE ETAPY")
    etapy = _parse_etapy()
    in_progress = [(e, s, b) for e, s, b in etapy if "IN PROGRESS" in s]
    todo = [(e, s, b) for e, s, b in etapy if "TODO" in s and "IN PROGRESS" not in s]

    sub("IN PROGRESS")
    if in_progress:
        for header, _, bullets in in_progress:
            bullet(header)
            for b in bullets:
                info(f"    {b}")
    else:
        info("(brak)")

    sub("TODO (kolejne w kolejce)")
    if todo:
        for header, _, _ in todo[:4]:
            bullet(header)
    else:
        info("(brak)")

    # ── 3. TODO/FIXME w kodzie ──────────────────────────────────
    h("3. TODO / FIXME W KODZIE (src/)")
    todos = _scan_todos()
    if todos:
        for rel, lineno, text in todos:
            info(f"{rel}:{lineno}  →  {text}")
    else:
        info("(brak — czysto)")

    # ── 4. Szybki stan danych ───────────────────────────────────
    h("4. STAN DANYCH")
    n_orders = _count_orders()
    bullet(f"Zamówienia w bazie: {n_orders}")
    bullet(f"Ścieżka danych: {ROOT / 'data'}")

    # ── 5. Priorytety na dziś ───────────────────────────────────
    h("5. PRIORYTETY NA DZIŚ — propozycja")
    info("Na podstawie aktywnych etapów:")
    info("")

    priorities: list[str] = []

    # Etap 1A: szybka wycena
    if any("1A" in e or "szybk" in e.lower() for e, _, _ in in_progress):
        priorities.append("Etap 1A — domknij jeden workflow szybkiej wyceny od A do Z")

    # Etap 3: statusy i kalendarz
    if any("Etap 3" in e or "status" in e.lower() or "kalendarz" in e.lower() for e, _, _ in in_progress):
        priorities.append("Etap 3 — dodaj brakujący status zamówienia lub popraw przepływ w Kalendarzu")

    # Etap 1: UX
    if any("Etap 1" in e and "1A" not in e for e, _, _ in in_progress):
        priorities.append("Etap 1 — poprawa UX na jednej karcie roboczej (max 2h)")

    # Fallback priorytety
    fallback = [
        "Napisz test smoke dla nowo dodanego kodu",
        "Przejrzyj TODO/FIXME wylistowane powyżej i rozwiąż jeden",
        "Sprawdź czy briefing biznesowy w aplikacji działa poprawnie",
    ]
    while len(priorities) < 3:
        priorities.append(fallback[len(priorities) % len(fallback)])

    for i, p in enumerate(priorities[:3], 1):
        info(f"  {i}. {p}")

    # ── Stopka ──────────────────────────────────────────────────
    lines.append("")
    lines.append("─" * 56)
    lines.append("  Dobrego dnia!")
    lines.append("─" * 56)
    lines.append("")

    return "\n".join(lines)


# ── Zapis i wydruk ────────────────────────────────────────────────────────────

def main() -> None:
    briefing = generate()
    print(briefing)

    # Zapisz do pliku obok skryptu
    try:
        OUTPUT_FILE.write_text(briefing, encoding="utf-8")
        print(f"\n[Zapisano: {OUTPUT_FILE}]")
    except Exception as e:
        print(f"\n[Nie można zapisać do pliku: {e}]", file=sys.stderr)


if __name__ == "__main__":
    # Wymusz UTF-8 na stdout (Windows cp1250 nie obsługuje polskich znaków)
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
