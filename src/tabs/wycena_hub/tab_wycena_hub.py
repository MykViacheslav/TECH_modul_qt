from __future__ import annotations

import traceback
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from src.tabs.wycena.unified_summary_panel import UnifiedSummaryPanel


def _safe_sub_tab(title: str, factory) -> QWidget:
    """Buduje widget podzakładki; przy błędzie zwraca placeholder zamiast crashować."""
    try:
        return factory()
    except Exception as exc:
        traceback.print_exc()
        w = QLabel(
            f"[{title}]\n\nNie udało się załadować widgetu.\n\n{type(exc).__name__}: {exc}"
        )
        w.setWordWrap(True)
        w.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        w.setStyleSheet("color:#b91c1c; padding:24px; font-size:12px;")
        return w


def _make_placeholder(label_text: str) -> QWidget:
    """Placeholder dla podzakładek jeszcze niezaimplementowanych."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl = QLabel(label_text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("color:#94a3b8; font-size:15px; font-weight:600;")
    lay.addWidget(lbl)
    return w


class _CuttingResultPanel(QWidget):
    """Minimalny panel read-only dla wyniku rozkroju (GiB Lab)."""

    def __init__(self, giblab_provider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._giblab_provider = giblab_provider

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("Rozkroj / wynik GiB Lab", self)
        title.setStyleSheet("font-size:16px; font-weight:800; color:#10233f;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        self.lab_empty = QLabel(
            "Brak danych rozkroju dla biezacego projektu/importu.\n"
            "Wczytaj wynik GiB Lab w zakladce 'Import 3D' (krok 5), a potem wroc tutaj.",
            self,
        )
        self.lab_empty.setWordWrap(True)
        self.lab_empty.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:10px;color:#475569;font-size:12px;}"
        )
        root.addWidget(self.lab_empty, 0)

        self.box = QFrame(self)
        self.box.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:12px;}"
        )
        grid = QGridLayout(self.box)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self._value_labels: dict[str, QLabel] = {}
        fields = [
            ("Liczba plyt (realnie)", "real_sheets_count"),
            ("Powierzchnia realna [m2]", "real_area_m2"),
            ("Odpad [m2]", "scrap_m2"),
            ("Wykorzystanie [%]", "utilization_pct"),
            ("Roznica vs teoria", "difference_vs_theory"),
        ]
        for row_idx, (label_text, key) in enumerate(fields):
            lab = QLabel(label_text, self.box)
            lab.setStyleSheet("color:#526174; font-size:11px; font-weight:700;")
            val = QLabel("-", self.box)
            val.setWordWrap(True)
            val.setStyleSheet("color:#10233f; font-size:13px; font-weight:800;")
            grid.addWidget(lab, row_idx, 0)
            grid.addWidget(val, row_idx, 1)
            self._value_labels[key] = val
        root.addWidget(self.box, 0)
        root.addStretch(1)

        self.refresh()

    def _set_empty(self) -> None:
        self.lab_empty.show()
        self.box.hide()
        for lbl in self._value_labels.values():
            lbl.setText("-")

    def refresh(self) -> None:
        model = None
        if callable(self._giblab_provider):
            try:
                model = self._giblab_provider()
            except Exception:
                model = None

        giblab = getattr(model, "giblab_result", None) if model is not None else None
        if giblab is None or not str(getattr(giblab, "result_path", "") or "").strip():
            self._set_empty()
            return

        diff_map = dict(getattr(giblab, "difference_vs_theory", {}) or {})
        utilization = float(diff_map.get("utilization_pct", 0.0) or 0.0)

        self.lab_empty.hide()
        self.box.show()
        self._value_labels["real_sheets_count"].setText(str(int(getattr(giblab, "real_sheets_count", 0) or 0)))
        self._value_labels["real_area_m2"].setText(f"{float(getattr(giblab, 'real_area_m2', 0.0) or 0.0):.3f}")
        self._value_labels["scrap_m2"].setText(f"{float(getattr(giblab, 'scrap_m2', 0.0) or 0.0):.3f}")
        self._value_labels["utilization_pct"].setText(f"{utilization:.2f}")
        self._value_labels["difference_vs_theory"].setText(
            json.dumps(diff_map, ensure_ascii=False, sort_keys=True) if diff_map else "{}"
        )


class _SummaryPanel(QWidget):
    def __init__(self, snapshot_provider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Podsumowanie wyceny", self)
        title.setStyleSheet("font-size:18px; font-weight:800; color:#10233f;")
        head.addWidget(title, 0)
        head.addStretch(1)
        self.btn_refresh = QPushButton("Odśwież", self)
        head.addWidget(self.btn_refresh, 0)
        root.addLayout(head)

        self.lab_scope = QLabel("", self)
        self.lab_scope.setWordWrap(True)
        self.lab_scope.setStyleSheet("color:#526174;")
        root.addWidget(self.lab_scope, 0, Qt.AlignmentFlag.AlignLeft)

        self.box = QFrame(self)
        self.box.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:14px;}"
        )
        box_layout = QGridLayout(self.box)
        box_layout.setContentsMargins(14, 14, 14, 14)
        box_layout.setHorizontalSpacing(16)
        box_layout.setVerticalSpacing(10)

        self._value_labels: dict[str, QLabel] = {}
        fields = [
            ("Techniczne", "technical_total"),
            ("Materiały", "material_value"),
            ("Transport", "transport"),
            ("Robocizna", "labor_cost"),
            ("Montaż", "montage"),
            ("Usługi dodatkowe", "extras_total"),
            ("Baza", "base_total"),
            ("Netto", "sale_total"),
            ("Brutto", "brutto_total"),
        ]
        for idx, (label, key) in enumerate(fields):
            r = idx // 3
            c = (idx % 3) * 2
            lab = QLabel(label, self.box)
            lab.setStyleSheet("color:#526174; font-size:11px; font-weight:700;")
            val = QLabel("—", self.box)
            val.setStyleSheet("color:#10233f; font-size:15px; font-weight:800;")
            box_layout.addWidget(lab, r, c)
            box_layout.addWidget(val, r, c + 1)
            self._value_labels[key] = val
        root.addWidget(self.box, 0)

        self.lab_report = QLabel("", self)
        self.lab_report.setWordWrap(True)
        self.lab_report.setStyleSheet("color:#334155; padding:4px 2px;")
        root.addWidget(self.lab_report, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_refresh.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        data = dict(self._snapshot_provider() or {})
        mode = str(data.get("mode", "") or "").strip()
        title = str(data.get("title", "") or "Podsumowanie").strip()
        if mode == "quick":
            client = str(data.get("client", "") or "").strip()
            quote_id = str(data.get("quote_id", "") or "").strip()
            scope = " / ".join(part for part in [title, quote_id, client] if part)
            self.lab_scope.setText(scope or "Szybka wycena")
            self._value_labels["technical_total"].setText(f"{float(data.get('material_value', 0.0) or 0.0):.2f} zl")
            self._value_labels["material_value"].setText(f"{float(data.get('material_value', 0.0) or 0.0):.2f} zl")
            self._value_labels["transport"].setText(f"{float(data.get('transport', 0.0) or 0.0):.2f} zl")
            self._value_labels["labor_cost"].setText(f"{float(data.get('labor_cost', 0.0) or 0.0):.2f} zl")
            self._value_labels["montage"].setText(f"{float(data.get('montage', 0.0) or 0.0):.2f} zl")
            self._value_labels["extras_total"].setText(f"{float(data.get('extras_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["base_total"].setText(f"{float(data.get('base_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["sale_total"].setText(f"{float(data.get('sale_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["brutto_total"].setText(f"{float(data.get('brutto_total', 0.0) or 0.0):.2f} zl")
            self.lab_report.setText(
                "Usługi dodatkowe są częścią końcowego kosztu szybkiej wyceny i trafiają do sumy bazowej."
            )
            return

        if mode == "assemblies":
            assembly = str(data.get("assembly", "") or "").strip()
            order = str(data.get("order", "") or "").strip()
            client = str(data.get("client", "") or "").strip()
            scope_parts = [title]
            if assembly:
                scope_parts.append(assembly)
            if order:
                scope_parts.append(order)
            if client:
                scope_parts.append(client)
            self.lab_scope.setText(" / ".join(scope_parts))
            self._value_labels["technical_total"].setText(f"{float(data.get('technical_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["material_value"].setText(f"{float(data.get('technical_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["transport"].setText(f"{float(data.get('transport_cost', 0.0) or 0.0):.2f} zl")
            self._value_labels["labor_cost"].setText(f"{float(data.get('labor_cost', 0.0) or 0.0):.2f} zl")
            self._value_labels["montage"].setText(f"{float(data.get('montage_cost', 0.0) or 0.0):.2f} zl")
            self._value_labels["extras_total"].setText("0.00 zl")
            self._value_labels["base_total"].setText(f"{float(data.get('base_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["sale_total"].setText(f"{float(data.get('sale_total', 0.0) or 0.0):.2f} zl")
            self._value_labels["brutto_total"].setText(f"{float(data.get('sale_total', 0.0) or 0.0):.2f} zl")
            self.lab_report.setText(str(data.get("report", "") or ""))
            return

        if mode == "import_3d":
            self.lab_scope.setText("Import 3D / rozpoznanie danych z pliku")
            self._value_labels["technical_total"].setText("—")
            self._value_labels["material_value"].setText("—")
            self._value_labels["transport"].setText("—")
            self._value_labels["labor_cost"].setText("—")
            self._value_labels["montage"].setText("—")
            self._value_labels["extras_total"].setText("—")
            self._value_labels["base_total"].setText("—")
            self._value_labels["sale_total"].setText("—")
            self._value_labels["brutto_total"].setText("—")
            self.lab_report.setText(str(data.get("report", "") or "Brak danych z importu."))
            return

        if mode == "services":
            self.lab_scope.setText("Usługi / pozycje dodatkowe")
            for key in self._value_labels:
                self._value_labels[key].setText("—")
            self.lab_report.setText(str(data.get("report", "") or "Usługi są częścią końcowej wyceny."))
            return

        if mode == "rozkroj":
            self.lab_scope.setText("Rozkrój / wynik po GiB Lab")
            for key in self._value_labels:
                self._value_labels[key].setText("—")
            self.lab_report.setText(str(data.get("report", "") or "Brak danych z rozkroju."))
            return

        self.lab_scope.setText(
            "Podsumowanie pojawi się po wybraniu Wycena projektu albo Szybka wycena."
        )
        for label in self._value_labels.values():
            label.setText("—")
        self.lab_report.setText("To miejsce zbiera końcowy wynik wyceny, w tym usługi dodatkowe.")


class TabWycenaHub(QWidget):
    """
    Hub nawigacyjny działu Wycena.

    Grupuje sześć trybów pracy w jednym miejscu:
      0 — Wycena projektu   (TabWycena)
      1 — Szybka wycena     (TabSzybkaWycena)
      2 — Import 3D         (TabSekcjaDoWyceny / 3DConstructor)
      3 — Usługi            (TabUslugi — wycena usług dla klienta)
      4 — Rozkrój           (placeholder)
      5 — Podsumowanie      (placeholder)

    Hub owna swoje instancje widgetów — nie są rejestrowane osobno w registry.py.
    Proxy open_assembly_for_pricing() zapewnia kompatybilność z MainWindow.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.lab_guide = QLabel("", self)
        self.lab_guide.setWordWrap(True)
        self.lab_guide.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:12px;"
            "padding:8px 12px;color:#334155;font-size:12px;font-weight:600;}"
        )
        root.addWidget(self.lab_guide, 0)

        self.mode_banner = QFrame(self)
        self.mode_banner.setStyleSheet(
            "QFrame{background:#eef6ff;border:1px solid #cfe3ff;border-radius:10px;}"
        )
        banner_lay = QVBoxLayout(self.mode_banner)
        banner_lay.setContentsMargins(10, 8, 10, 8)
        banner_lay.setSpacing(2)
        self.lab_mode_title = QLabel("", self.mode_banner)
        self.lab_mode_title.setStyleSheet("font-size:12px;font-weight:800;color:#10233f;")
        self.lab_mode_desc = QLabel("", self.mode_banner)
        self.lab_mode_desc.setWordWrap(True)
        self.lab_mode_desc.setStyleSheet("font-size:11px;color:#334155;")
        banner_lay.addWidget(self.lab_mode_title)
        banner_lay.addWidget(self.lab_mode_desc)
        root.addWidget(self.mode_banner, 0)

        self._sub_tabs = QTabWidget(self)
        self._sub_tabs.setDocumentMode(True)
        root.addWidget(self._sub_tabs)
        self._summary_source_index = 0

        # ── Wycena projektu ──────────────────────────────────────────────────
        self._tab_wycena = _safe_sub_tab(
            "Wycena projektu",
            lambda: __import__(
                "src.tabs.wycena.tab_wycena", fromlist=["TabWycena"]
            ).TabWycena(),
        )
        self._sub_tabs.addTab(self._tab_wycena, "Wycena projektu")

        # ── Szybka wycena ────────────────────────────────────────────────────
        self._tab_szybka = _safe_sub_tab(
            "Szybka wycena",
            lambda: __import__(
                "src.tabs.szybka_wycena.tab_szybka_wycena", fromlist=["TabSzybkaWycena"]
            ).TabSzybkaWycena(),
        )
        self._sub_tabs.addTab(self._tab_szybka, "Szybka wycena")

        # ── Import 3D ────────────────────────────────────────────────────────
        self._tab_3dc = _safe_sub_tab(
            "Import 3D",
            lambda: __import__(
                "src.tabs.sekcja_do_wyceny.tab_sekcja_do_wyceny",
                fromlist=["TabSekcjaDoWyceny"],
            ).TabSekcjaDoWyceny(),
        )
        self._sub_tabs.addTab(self._tab_3dc, "Import 3D")

        # ── Usługi — wycena usług dla klienta ───────────────────────────────
        # Definicje usług (cennik) dostępne są w Bazy → Baza usług.
        self._tab_uslugi = _safe_sub_tab(
            "Usługi",
            lambda: __import__(
                "src.tabs.uslugi.tab_uslugi", fromlist=["TabUslugi"]
            ).TabUslugi(),
        )
        self._sub_tabs.addTab(self._tab_uslugi, "Usługi")

        # ── Rozkrój — minimalny panel read-only ──────────────────────────────
        self._tab_rozkroj = _CuttingResultPanel(self._get_giblab_model, self)
        self._sub_tabs.addTab(self._tab_rozkroj, "Rozkrój")

        # ── Podsumowanie — ujednolicone ─────────────────────────────────────
        self._summary_panel = UnifiedSummaryPanel(
            quick_quote_provider=self._get_quick_quote_model,
            service_provider=self._get_service_model,
            import_3d_provider=self._get_import_3d_model,
            assembly_provider=self._get_assembly_model,
            giblab_provider=self._get_giblab_model,
            parent=self
        )
        self._sub_tabs.addTab(self._summary_panel, "Podsumowanie")

        self._sub_tabs.currentChanged.connect(self._on_sub_tab_changed)

        self._summary_panel.refresh()
        self._update_guide_text()

    # ── Kompatybilność z MainWindow._open_assembly_in_wycena ────────────────

    def open_assembly_for_pricing(self, assembly_name: str) -> None:
        """
        Przełącza na podzakładkę 'Wycena projektu' i przekazuje nazwę assembly.
        Zachowuje kompatybilność z MainWindow._open_assembly_in_wycena.
        """
        self._sub_tabs.setCurrentIndex(0)
        if hasattr(self._tab_wycena, "open_assembly_for_pricing"):
            self._tab_wycena.open_assembly_for_pricing(str(assembly_name or ""))

    def _on_sub_tab_changed(self, index: int) -> None:
        summary_index = self._sub_tabs.indexOf(self._summary_panel) if hasattr(self, "_summary_panel") else -1
        if index != summary_index:
            self._summary_source_index = index
        if index == 4 and hasattr(self, "_tab_rozkroj") and hasattr(self._tab_rozkroj, "refresh"):
            self._tab_rozkroj.refresh()
        if index == summary_index:
            self._summary_panel.refresh()
        self._update_guide_text(index)

    def _guide_text_for_index(self, index: int) -> str:
        if index == 0:
            return "Wycena projektu: wybierz komplet, moduł albo ścianę, a potem sprawdź dane techniczne i koszty."
        if index == 1:
            return "Szybka wycena: wybierz szybki wpis albo dodaj nową ofertę handlową bez pełnej struktury projektu."
        if index == 2:
            return "Import 3D: wczytaj plik, sprawdź rozpoznanie danych i przygotuj mapowanie materiałów."
        if index == 3:
            return "Usługi: dodaj pozycje dodatkowe i dopilnuj, żeby pojawiły się w końcowym podsumowaniu."
        if index == 4:
            return "Rozkrój: po GiB Lab porównaj teorię z wynikiem rzeczywistym, odpadami i liczbą płyt."
        return "Podsumowanie: tutaj widzisz końcowy wynik wyceny, usług i rozkroju."

    def _update_guide_text(self, index: int | None = None) -> None:
        if index is None:
            index = self._sub_tabs.currentIndex()
        idx = int(index)
        self.lab_guide.setText(self._guide_text_for_index(idx))
        self._update_mode_banner(idx)

    def _update_mode_banner(self, index: int) -> None:
        if index == 0:
            self.mode_banner.setStyleSheet(
                "QFrame{background:#eef6ff;border:1px solid #cfe3ff;border-radius:10px;}"
            )
            self.lab_mode_title.setText("TRYB SYSTEMOWY: WYCENA PROJEKTU")
            self.lab_mode_desc.setText(
                "Uzyj tego trybu, gdy liczysz z danych technicznych modułu/kompletu/sciany. "
                "Dla szybkiej oferty handlowej bez pelnej struktury przejdz do 'Szybka wycena'."
            )
            return
        if index == 1:
            self.mode_banner.setStyleSheet(
                "QFrame{background:#ecfdf5;border:1px solid #c7f3dd;border-radius:10px;}"
            )
            self.lab_mode_title.setText("TRYB HANDLOWY: SZYBKA WYCENA")
            self.lab_mode_desc.setText(
                "Uzyj tego trybu, gdy potrzebujesz szybkiej oferty dla klienta. "
                "Do pelnej kalkulacji technicznej przejdz do 'Wycena projektu'."
            )
            return

        self.mode_banner.setStyleSheet(
            "QFrame{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;}"
        )
        self.lab_mode_title.setText("TRYB UZUPELNIAJACY")
        self.lab_mode_desc.setText("Pracujesz w trybie pomocniczym huba Wycena.")

    def _current_summary_snapshot(self) -> dict[str, object]:
        summary_index = self._sub_tabs.indexOf(self._summary_panel) if hasattr(self, "_summary_panel") else -1
        active_index = self._sub_tabs.currentIndex()
        if active_index == summary_index:
            return {
                "mode": "summary",
                "title": "Podsumowanie",
                "report": "Końcowe podsumowanie zbiera wycenę projektu, szybkie wyceny, usługi i wynik rozkroju.",
            }

        if self._summary_source_index == 0 or self._summary_source_index == 1:
            if hasattr(self._tab_wycena, "get_summary_snapshot"):
                snap = self._tab_wycena.get_summary_snapshot()
                if isinstance(snap, dict):
                    return snap
        if self._summary_source_index == 2:
            return {
                "mode": "import_3d",
                "title": "Import 3D",
                "report": "Podsumowanie importu 3D pokaże się po wczytaniu projektu i wyników z GiB Lab.",
            }
        if self._summary_source_index == 3:
            return {
                "mode": "services",
                "title": "Usługi",
                "report": "Usługi z tej części trafiają do końcowego podsumowania wyceny jako pozycje dodatkowe.",
            }
        if self._summary_source_index == 4:
            return {
                "mode": "rozkroj",
                "title": "Rozkrój",
                "report": "Rozkrój pokaże wyniki po GiB Lab, liczbę płyt, odpady i różnicę względem teorii.",
            }
        return {
            "mode": "summary",
            "title": "Podsumowanie",
            "report": "Końcowe podsumowanie zbiera wycenę projektu, szybkie wyceny, usługi i wynik rozkroju.",
        }

    def get_project_model(self):
        active = self._sub_tabs.currentWidget()
        if active is None:
            return None
        getter = getattr(active, "get_project_model", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    # ── Providers for UnifiedSummaryPanel ────────────────────────────────────

    def _get_assembly_model(self):
        """Get ProjectModel from Wycena projektu tab (index 0)."""
        if hasattr(self, "_tab_wycena") and hasattr(self._tab_wycena, "get_project_model"):
            try:
                return self._tab_wycena.get_project_model()
            except Exception:
                pass
        return None

    def _get_quick_quote_model(self):
        """Get ProjectModel from Szybka wycena tab (index 1)."""
        if hasattr(self, "_tab_szybka") and hasattr(self._tab_szybka, "get_project_model"):
            try:
                return self._tab_szybka.get_project_model()
            except Exception:
                pass
        return None

    def _get_import_3d_model(self):
        """Get ProjectModel from Import 3D tab (index 2)."""
        if hasattr(self, "_tab_3dc") and hasattr(self._tab_3dc, "get_project_model"):
            try:
                return self._tab_3dc.get_project_model()
            except Exception:
                pass
        return None

    def _get_service_model(self):
        """Get ProjectModel from Usługi tab (index 3)."""
        if hasattr(self, "_tab_uslugi") and hasattr(self._tab_uslugi, "get_project_model"):
            try:
                return self._tab_uslugi.get_project_model()
            except Exception:
                pass
        return None

    def _get_giblab_model(self):
        """Get ProjectModel with GiB Lab result from Import 3D tab (index 2)."""
        if hasattr(self, "_tab_3dc") and hasattr(self._tab_3dc, "get_project_model"):
            try:
                return self._tab_3dc.get_project_model()
            except Exception:
                pass
        return None
