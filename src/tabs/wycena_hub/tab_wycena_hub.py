from __future__ import annotations

import traceback
import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from src.app.app_settings import load_ui_theme_settings
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


class _CuttingResultPanel(QWidget):
    """Minimalny panel read-only dla wyniku rozkroju (GiB Lab)."""

    def __init__(self, giblab_provider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._giblab_provider = giblab_provider

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        theme = load_ui_theme_settings()
        is_tech_night = (
            str(theme.motif or "").strip().lower() == "tech"
            and str(theme.mode or "").strip().lower() == "night"
        )
        c_text = "#e8efff" if is_tech_night else "#0f172a"

        title = QLabel("Rozkrój / wynik GiB Lab", self)
        title.setStyleSheet(f"font-size:16px; font-weight:800; color:{c_text};")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        self.lab_empty = QLabel(
            "Brak danych rozkroju dla bieżącego projektu/importu.\n"
            "Wczytaj wynik GiB Lab w zakładce 'Wycena' (tryb Import 3D), a potem wróć tutaj.",
            self,
        )
        self.lab_empty.setWordWrap(True)
        self.lab_empty.setStyleSheet(
            "QLabel{background:transparent;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:10px;color:#94a3b8;font-size:12px;}"
        )
        root.addWidget(self.lab_empty, 0)

        self.box = QFrame(self)
        self.box.setProperty("uiCard", True)
        self.box.setStyleSheet(
            "QFrame{background:transparent;border:1px solid #d7e1ef;border-radius:12px;}"
        )
        grid = QGridLayout(self.box)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self._value_labels: dict[str, QLabel] = {}
        fields = [
            ("Liczba płyt (realnie)", "real_sheets_count"),
            ("Powierzchnia realna [m2]", "real_area_m2"),
            ("Odpad [m2]", "scrap_m2"),
            ("Wykorzystanie [%]", "utilization_pct"),
            ("Różnica vs teoria", "difference_vs_theory"),
        ]
        for row_idx, (label_text, key) in enumerate(fields):
            lab = QLabel(label_text, self.box)
            lab.setStyleSheet("color:#94a3b8; font-size:11px; font-weight:700;")
            val = QLabel("-", self.box)
            val.setWordWrap(True)
            val.setStyleSheet(f"color:{c_text}; font-size:13px; font-weight:800;")
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
        self._value_labels["real_sheets_count"].setText(
            str(int(getattr(giblab, "real_sheets_count", 0) or 0))
        )
        self._value_labels["real_area_m2"].setText(
            f"{float(getattr(giblab, 'real_area_m2', 0.0) or 0.0):.3f}"
        )
        self._value_labels["scrap_m2"].setText(
            f"{float(getattr(giblab, 'scrap_m2', 0.0) or 0.0):.3f}"
        )
        self._value_labels["utilization_pct"].setText(f"{utilization:.2f}")
        self._value_labels["difference_vs_theory"].setText(
            json.dumps(diff_map, ensure_ascii=False, sort_keys=True) if diff_map else "{}"
        )


class TabWycenaHub(QWidget):
    """
    Hub nawigacyjny działu Wycena, ujednolicony dla Projektu, Handlowej i Importu 3D.
    """
    sig_open_order_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.lab_guide = QLabel("", self)
        self.lab_guide.setWordWrap(True)
        self.lab_guide.setStyleSheet(
            "QLabel{background:transparent;border:1px solid #d7e1ef;border-radius:12px;"
            "padding:8px 12px;color:#334155;font-size:12px;font-weight:600;}"
        )
        root.addWidget(self.lab_guide, 0)

        self.mode_banner = QFrame(self)
        self.mode_banner.setProperty("uiCard", True)
        self.mode_banner.setStyleSheet("QFrame { border-radius: 10px; }")
        banner_lay = QVBoxLayout(self.mode_banner)
        banner_lay.setContentsMargins(10, 8, 10, 8)
        banner_lay.setSpacing(2)
        self.lab_mode_title = QLabel("", self.mode_banner)
        self.lab_mode_title.setStyleSheet("font-size:12px;font-weight:800;color:#e8efff;")
        self.lab_mode_desc = QLabel("", self.mode_banner)
        self.lab_mode_desc.setWordWrap(True)
        self.lab_mode_desc.setStyleSheet("font-size:11px;color:#94a3b8;")
        banner_lay.addWidget(self.lab_mode_title)
        banner_lay.addWidget(self.lab_mode_desc)
        root.addWidget(self.mode_banner, 0)

        self.nav_bar = QHBoxLayout()
        self.nav_bar.setContentsMargins(10, 4, 10, 4)
        self.btn_back_to_order = QPushButton("◀ Wróć do Zamówienia", self)
        self.btn_back_to_order.setMinimumHeight(28)
        self.btn_back_to_order.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back_to_order.setFixedWidth(160)
        self.btn_back_to_order.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.btn_back_to_order.setStyleSheet(
            "QPushButton {"
            "  background: #1d4ed8; color: white; border-radius: 6px; font-weight: 800; padding: 4px 12px; font-size: 11px;"
            "} "
            "QPushButton:hover { background: #2563eb; }"
        )
        self.btn_back_to_order.clicked.connect(self.sig_open_order_requested.emit)
        self.nav_bar.addWidget(self.btn_back_to_order, 0)
        self.nav_bar.addStretch(1)
        root.addLayout(self.nav_bar)

        self._sub_tabs = QTabWidget(self)
        self._sub_tabs.setDocumentMode(True)
        root.addWidget(self._sub_tabs)
        self._summary_source_index = 0

        # Wycena zintegrowana
        self._tab_wycena = _safe_sub_tab(
            "Wycena",
            lambda: __import__(
                "src.tabs.wycena.tab_wycena", fromlist=["TabWycena"]
            ).TabWycena(),
        )
        self._sub_tabs.addTab(self._tab_wycena, "Wycena (Projekt/Handlowa/3D)")

        # Usługi
        self._tab_uslugi = _safe_sub_tab(
            "Usługi",
            lambda: __import__(
                "src.tabs.uslugi.tab_uslugi", fromlist=["TabUslugi"]
            ).TabUslugi(),
        )
        self._sub_tabs.addTab(self._tab_uslugi, "Usługi")

        # Rozkrój
        self._tab_rozkroj = _CuttingResultPanel(self._get_giblab_model, self)
        self._sub_tabs.addTab(self._tab_rozkroj, "Rozkrój")

        # Podsumowanie
        self._summary_panel = UnifiedSummaryPanel(
            quick_quote_provider=self._get_quick_quote_model,
            service_provider=self._get_service_model,
            import_3d_provider=self._get_import_3d_model,
            assembly_provider=self._get_assembly_model,
            giblab_provider=self._get_giblab_model,
            parent=self,
        )
        self._sub_tabs.addTab(self._summary_panel, "Podsumowanie")

        self._sub_tabs.currentChanged.connect(self._on_sub_tab_changed)
        self._update_guide_text()

    def open_assembly_for_pricing(self, assembly_name: str) -> None:
        self._sub_tabs.setCurrentIndex(0)
        if hasattr(self._tab_wycena, "open_assembly_for_pricing"):
            self._tab_wycena.open_assembly_for_pricing(str(assembly_name or ""))

    def _on_sub_tab_changed(self, index: int) -> None:
        summary_index = self._sub_tabs.indexOf(self._summary_panel)
        if index != summary_index:
            self._summary_source_index = index
        if index == 2 and hasattr(self._tab_rozkroj, "refresh"):
            self._tab_rozkroj.refresh()
        if index == summary_index:
            self._summary_panel.refresh()
        self._update_guide_text(index)

    def _guide_text_for_index(self, index: int) -> str:
        if index == 0:
            return "Wycena: użyj przełącznika 'Tryb wyceny', aby wybrać Projekt, Szybką wycenę handlową lub Import 3D."
        if index == 1:
            return "Usługi: dodaj pozycje dodatkowe (montaż, poprawki, materiały pomocnicze)."
        if index == 2:
            return "Rozkrój: sprawdź wynik z GiB Lab, odpady i liczbę płyt po optymalizacji."
        return "Podsumowanie: zbiera wszystkie koszty w jedną końcową ofertę."

    def _update_guide_text(self, index: int | None = None) -> None:
        if index is None:
            index = self._sub_tabs.currentIndex()
        idx = int(index)
        self.lab_guide.setText(self._guide_text_for_index(idx))
        self._update_mode_banner(idx)

    def _update_mode_banner(self, index: int) -> None:
        if index == 0:
            self.mode_banner.setStyleSheet(
                "QFrame{border:1px solid #3b82f6;border-radius:10px;}"
            )
            self.lab_mode_title.setStyleSheet(
                "font-size:12px;font-weight:800;color:#60a5fa;"
            )
            self.lab_mode_title.setText("ZINTEGROWANA WYCENA")
            self.lab_mode_desc.setText(
                "Wybierz tryb (Projektowa, Handlowa lub Import 3D) w polu 'Tryb wyceny' powyżej."
            )
            return

        self.mode_banner.setStyleSheet(
            "QFrame{border:1px solid #64748b;border-radius:10px;}"
        )
        self.lab_mode_title.setStyleSheet(
            "font-size:12px;font-weight:800;color:#94a3b8;"
        )
        self.lab_mode_title.setText("TRYB UZUPEŁNIAJĄCY")
        self.lab_mode_desc.setText("Pracujesz w trybie pomocniczym huba Wycena.")

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

    def _get_assembly_model(self):
        if hasattr(self, "_tab_wycena") and hasattr(self._tab_wycena, "get_project_model"):
            try:
                return self._tab_wycena.get_project_model()
            except Exception:
                pass
        return None

    def _get_quick_quote_model(self):
        return self._get_assembly_model()

    def _get_import_3d_model(self):
        return self._get_assembly_model()

    def _get_service_model(self):
        if hasattr(self, "_tab_uslugi") and hasattr(self._tab_uslugi, "get_project_model"):
            try:
                return self._tab_uslugi.get_project_model()
            except Exception:
                pass
        return None

    def _get_giblab_model(self):
        return self._get_assembly_model()