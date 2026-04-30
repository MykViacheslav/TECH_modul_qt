from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from src.services.constructor_3dc_quote_import_service import (
    Constructor3dcQuoteImportData,
    Constructor3dcQuoteImportError,
    ImportControlRow,
    parse_3dc_project_for_quote_import,
)
from src.services.project_model_giblab_adapter import attach_giblab_result, build_giblab_result_from_project_file
from src.services.project_model_import_adapter import build_import_3d_project_model
from src.domain.project_model import ProjectGibLabResult, ProjectModel
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.constructor_3dc_mapping_store_json import Constructor3dcMappingStoreJson


class DialogImport3dcWycena(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import z 3D-konstruktora")
        self.resize(1500, 940)
        self.setStyleSheet(
            """
            QDialog { background:#eef2f8; }
            QTabWidget::pane { border:0; }
            QTabBar::tab {
                background:transparent;
                border:1px solid #cfd8e6;
                border-radius:14px;
                padding:8px 14px;
                margin-right:6px;
                color:#1f2a44;
                font-weight:600;
            }
            QTabBar::tab:selected {
                background:#e8eefb;
                border:1px solid #1f2a44;
            }
            QTableWidget {
                background:transparent;
                border:1px solid #d9e0ea;
                border-radius:8px;
                gridline-color:#e5e7eb;
            }
            QHeaderView::section {
                background:#f3f5f9;
                border:0;
                border-bottom:1px solid #d9e0ea;
                padding:6px;
                font-weight:600;
                color:#334155;
            }
            QPushButton {
                background:transparent;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:6px 10px;
            }
            QPushButton:hover { background:transparent; }
            """
        )

        self._catalog = CatalogStoreJson()
        self._mapping_store = Constructor3dcMappingStoreJson()
        self._mapping = self._mapping_store.load()
        self._import_data: Constructor3dcQuoteImportData | None = None
        self._project_model: ProjectModel | None = None
        self._giblab_result: ProjectGibLabResult | None = None
        self._giblab_result_path: Path | None = None
        self._loaded_path: Path | None = None
        self._created_entry: dict[str, Any] | None = None
        self._created_assembly: dict[str, Any] | None = None
        self._transfer_target: str = "quick"
        self._pricing_rows_cache: list[dict[str, Any]] = []
        self._mapping_combo_by_row: dict[int, QComboBox] = {}
        self._mapping_key_by_row: dict[int, tuple[str, str]] = {}
        self._suspend_mapping_events = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.btn_import = QPushButton("📂 Import", self)
        self.btn_open_folder = QPushButton("📁 Folder", self)
        self.btn_refresh = QPushButton("🔄 Odswiez", self)
        self.btn_transfer = QPushButton("🛒 Wczytaj", self)
        self.btn_cancel = QPushButton("❌ Anuluj", self)
        self.btn_open_giblab = QPushButton("🚀 GiB Lab", self)
        self.btn_load_gib_result = QPushButton("📥 Wynik", self)
        self.btn_go_mapping = QPushButton("🗺️ Mapuj", self)
        self.btn_save_mapping = QPushButton("💾 Zapisz", self)
        for btn in (
            self.btn_import,
            self.btn_open_folder,
            self.btn_refresh,
            self.btn_transfer,
            self.btn_cancel,
            self.btn_go_mapping,
            self.btn_open_giblab,
            self.btn_load_gib_result,
            self.btn_save_mapping,
        ):
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.setFixedWidth(100)
            actions.addWidget(btn, 0)
        
        self.btn_import.setFixedWidth(110)
        self.btn_transfer.setFixedWidth(110)
        self.btn_open_giblab.setFixedWidth(120)
        self.btn_load_gib_result.setFixedWidth(110)
        
        actions.addStretch(1)
        actions.addWidget(QLabel("Cel importu:", self), 0)
        self.cb_target = QComboBox(self)
        self.cb_target.addItem("Szybka wycena", "quick")
        self.cb_target.addItem("Komplety (Wycena)", "assemblies")
        self.cb_target.setMinimumWidth(190)
        actions.addWidget(self.cb_target, 0)
        root.addLayout(actions)

        self.lab_file = QLabel("Plik: [brak]", self)
        self.lab_file.setStyleSheet("color:#475467;")
        root.addWidget(self.lab_file, 0, Qt.AlignmentFlag.AlignLeft)

        summary_frame = QFrame(self); summary_frame.setProperty("uiCard", True)
        summary_frame.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:transparent; }")
        summary_grid = QGridLayout(summary_frame)
        summary_grid.setContentsMargins(10, 8, 10, 8)
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(6)
        self._summary_labels: dict[str, QLabel] = {}
        fields = [
            ("project_name", "Nazwa projektu"),
            ("module_name", "Nazwa modulu"),
            ("dims", "Wymiary"),
            ("counts", "Pozycje"),
            ("area", "Powierzchnia plyt [m2]"),
            ("edge", "Okleina [mb]"),
            ("status", "Status importu"),
        ]
        for idx, (key, title) in enumerate(fields):
            row = idx // 2
            col = (idx % 2) * 2
            summary_grid.addWidget(QLabel(f"{title}:", summary_frame), row, col)
            val = QLabel("-", summary_frame)
            val.setStyleSheet("font-weight:700; color:#e8efff;")
            summary_grid.addWidget(val, row, col + 1)
            self._summary_labels[key] = val
        root.addWidget(summary_frame, 0)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        root.addLayout(kpi_row)
        self.lab_kpi_elements = QLabel("0", self)
        self.lab_kpi_area = QLabel("0.00 m2", self)
        self.lab_kpi_edge = QLabel("0.00 mb", self)
        self.lab_kpi_mapping = QLabel("0%", self)
        cards = [
            ("Elementy do importu", self.lab_kpi_elements),
            ("Powierzchnia plyt", self.lab_kpi_area),
            ("Okleina", self.lab_kpi_edge),
            ("Mapowanie materialow", self.lab_kpi_mapping),
        ]
        for title, val in cards:
            card = QFrame(self); card.setProperty("uiCard", True)
            card.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:12px; background:transparent; }")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(10, 8, 10, 8)
            t = QLabel(title, card)
            t.setStyleSheet("color:#64748b;")
            val.setParent(card)
            val.setStyleSheet("font-size:26px; font-weight:800; color:#0f172a;")
            lay.addWidget(t, 0)
            lay.addWidget(val, 0)
            lay.addStretch(1)
            kpi_row.addWidget(card, 1)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        tab_import = QWidget(self.tabs)
        lay_import = QVBoxLayout(tab_import)
        lay_import.setContentsMargins(8, 8, 8, 8)
        lay_import.setSpacing(8)
        intro = QLabel(
            "Krok 1: import projektu i szybki podglad. "
            "Kontrola, mapowanie i wycena sa w kolejnych podzakladkach.",
            tab_import,
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#667085;")
        lay_import.addWidget(intro, 0)

        import_split = QHBoxLayout()
        import_split.setSpacing(8)
        lay_import.addLayout(import_split, 1)

        import_left = QFrame(tab_import)
        import_left.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:transparent; }")
        import_left_lay = QVBoxLayout(import_left)
        import_left_lay.setContentsMargins(10, 10, 10, 10)
        import_left_lay.setSpacing(8)
        import_left_lay.addWidget(QLabel("Podstawowe informacje projektu", import_left), 0)
        self.lab_preview_module = QLabel("-", import_left)
        self.lab_preview_dims = QLabel("-", import_left)
        self.lab_preview_materials = QLabel("-", import_left)
        self.lab_preview_materials.setWordWrap(True)
        self.lab_preview_cost = QLabel("0.00 zl", import_left)
        self.lab_preview_cost.setStyleSheet("font-weight:700;")
        import_left_lay.addWidget(self.lab_preview_module, 0)
        import_left_lay.addWidget(self.lab_preview_dims, 0)
        import_left_lay.addWidget(self.lab_preview_materials, 0)
        import_left_lay.addWidget(self.lab_preview_cost, 0)
        import_left_lay.addStretch(1)
        import_split.addWidget(import_left, 3)

        import_right = QFrame(tab_import)
        import_right.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:transparent; }")
        import_right_lay = QVBoxLayout(import_right)
        import_right_lay.setContentsMargins(10, 10, 10, 10)
        import_right_lay.setSpacing(8)
        import_right_lay.addWidget(QLabel("Gotowosc do importu", import_right), 0)
        self.pb_readiness = QProgressBar(import_right)
        self.pb_readiness.setRange(0, 100)
        self.pb_readiness.setValue(0)
        import_right_lay.addWidget(self.pb_readiness, 0)
        self.lab_ready_pct = QLabel("0%", import_right)
        self.lab_ready_formatki = QLabel("Formatki: -", import_right)
        self.lab_ready_fronty = QLabel("Fronty: -", import_right)
        self.lab_ready_okucia = QLabel("Okucia: -", import_right)
        self.lab_ready_materials = QLabel("Materialy: -", import_right)
        for w in (self.lab_ready_pct, self.lab_ready_formatki, self.lab_ready_fronty, self.lab_ready_okucia, self.lab_ready_materials):
            import_right_lay.addWidget(w, 0)
        import_right_lay.addStretch(1)
        import_split.addWidget(import_right, 2)

        tab_control = QWidget(self.tabs)
        lay_control = QVBoxLayout(tab_control)
        lay_control.setContentsMargins(8, 8, 8, 8)
        lay_control.setSpacing(8)
        control_head = QLabel("Krok 2: kontrola danych z importu przed przeniesieniem do wyceny.", tab_control)
        control_head.setStyleSheet("color:#667085;")
        lay_control.addWidget(control_head, 0)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Szukaj:", tab_control), 0)
        self.ed_filter = QLineEdit(tab_control)
        self.ed_filter.setPlaceholderText("Filtr tabeli kontroli importu...")
        filter_row.addWidget(self.ed_filter, 1)
        filter_row.addWidget(QLabel("Sekcja:", tab_control), 0)
        self.cb_control_section = QComboBox(tab_control)
        self.cb_control_section.addItem("Wszystkie", "")
        for sec in ("Formatka", "Front", "Okucie", "Lacznik", "Operacja"):
            self.cb_control_section.addItem(sec, sec)
        filter_row.addWidget(self.cb_control_section, 0)
        lay_control.addLayout(filter_row)

        self.tbl_control = QTableWidget(0, 14, tab_control)
        self.tbl_control.setHorizontalHeaderLabels(
            [
                "Sekcja",
                "Kod",
                "Nazwa",
                "Ilosc",
                "Dlugosc mm",
                "Szerokosc mm",
                "Grubosc mm",
                "Material z importu",
                "Okleina / opis",
                "Okleina mb",
                "Powierzchnia m2",
                "Status",
                "Zrodlo",
                "ID zrodlowe",
            ]
        )
        self.tbl_control.verticalHeader().setVisible(False)
        self.tbl_control.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_control.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hc = self.tbl_control.horizontalHeader()
        hc.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hc.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hc.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for col in (3, 4, 5, 6, 9, 10, 11):
            hc.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hc.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        hc.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        hc.setSectionResizeMode(12, QHeaderView.ResizeMode.ResizeToContents)
        hc.setSectionResizeMode(13, QHeaderView.ResizeMode.ResizeToContents)
        lay_control.addWidget(QLabel("Tabela kontroli importu", tab_control), 0)
        lay_control.addWidget(self.tbl_control, 1)

        tab_pricing = QWidget(self.tabs)
        lay_pricing = QHBoxLayout(tab_pricing)
        lay_pricing.setContentsMargins(8, 8, 8, 8)
        lay_pricing.setSpacing(8)

        pricing_side = QFrame(tab_pricing)
        pricing_side.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:transparent; }")
        pricing_side_lay = QVBoxLayout(pricing_side)
        pricing_side_lay.setContentsMargins(10, 10, 10, 10)
        pricing_side_lay.setSpacing(8)
        pricing_side_lay.addWidget(QLabel("Podsumowanie wyceny", pricing_side), 0)
        self.lab_sum_material_card = QLabel("Materialy: 0.00 zl", pricing_side)
        self.lab_sum_edge_card = QLabel("Okleina: 0.00 zl", pricing_side)
        self.lab_sum_labor_card = QLabel("Robocizna: 0.00 zl", pricing_side)
        self.lab_sum_total_card = QLabel("Razem: 0.00 zl", pricing_side)
        self.lab_sum_total_card.setStyleSheet("font-weight:700;")
        for w in (self.lab_sum_material_card, self.lab_sum_edge_card, self.lab_sum_labor_card, self.lab_sum_total_card):
            pricing_side_lay.addWidget(w, 0)
        pricing_side_lay.addStretch(1)
        lay_pricing.addWidget(pricing_side, 1)

        pricing_main = QVBoxLayout()
        pricing_main.setSpacing(8)
        lay_pricing.addLayout(pricing_main, 5)

        pricing_filter = QHBoxLayout()
        pricing_filter.addWidget(QLabel("Grupa:", tab_pricing), 0)
        self.cb_pricing_group = QComboBox(tab_pricing)
        self.cb_pricing_group.addItem("Wszystkie", "")
        for sec in ("Korpus", "Fronty", "Okucia", "Laczniki", "Operacje"):
            self.cb_pricing_group.addItem(sec, sec)
        pricing_filter.addWidget(self.cb_pricing_group, 0)
        pricing_filter.addStretch(1)
        pricing_main.addLayout(pricing_filter)

        self.tbl_pricing = QTableWidget(0, 22, tab_pricing)
        self.tbl_pricing.setHorizontalHeaderLabels(
            [
                "Grupa",
                "Pozycja",
                "Zrodlo",
                "Material",
                "Gr [mm]",
                "L [mm]",
                "W [mm]",
                "Ilosc",
                "Okleina L",
                "Okleina P",
                "Okleina G",
                "Okleina D",
                "Suma okleiny [mb]",
                "Powierzchnia [m2]",
                "Cena mat. [zl/m2]",
                "Cena okleiny [zl/mb]",
                "Koszt materialu [zl]",
                "Koszt okleiny [zl]",
                "Robocizna [zl]",
                "Koszt dodatkowy [zl]",
                "Wartosc pozycji [zl]",
                "Uwagi",
            ]
        )
        self.tbl_pricing.verticalHeader().setVisible(False)
        self.tbl_pricing.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_pricing.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hp = self.tbl_pricing.horizontalHeader()
        hp.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hp.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for col in (4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20):
            hp.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(21, QHeaderView.ResizeMode.Stretch)
        pricing_main.addWidget(QLabel("Tabela wyceny po imporcie", tab_pricing), 0)
        pricing_main.addWidget(self.tbl_pricing, 1)

        self.lab_totals = QLabel("Materialy: 0.00 zl | Okleina: 0.00 zl | Robocizna: 0.00 zl | Razem: 0.00 zl", tab_pricing)
        self.lab_totals.setStyleSheet("font-weight:700; color:#0f172a;")
        pricing_main.addWidget(self.lab_totals, 0, Qt.AlignmentFlag.AlignRight)

        tab_mapping = QWidget(self.tabs)
        lay_mapping = QHBoxLayout(tab_mapping)
        lay_mapping.setContentsMargins(8, 8, 8, 8)
        lay_mapping.setSpacing(8)

        mapping_left = QVBoxLayout()
        mapping_left.setSpacing(8)
        lay_mapping.addLayout(mapping_left, 3)

        self.tbl_mapping = QTableWidget(0, 4, tab_mapping)
        self.tbl_mapping.setHorizontalHeaderLabels(["Typ", "Material z importu", "Mapowanie lokalne", "Status"])
        self.tbl_mapping.verticalHeader().setVisible(False)
        self.tbl_mapping.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hm = self.tbl_mapping.horizontalHeader()
        hm.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hm.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hm.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hm.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        mapping_left.addWidget(QLabel("Mapowanie materialow z importu", tab_mapping), 0)
        mapping_left.addWidget(self.tbl_mapping, 1)

        mapping_right = QFrame(tab_mapping)
        mapping_right.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:transparent; }")
        mapping_right_lay = QVBoxLayout(mapping_right)
        mapping_right_lay.setContentsMargins(10, 10, 10, 10)
        mapping_right_lay.setSpacing(8)
        mapping_right_lay.addWidget(QLabel("Akcje", mapping_right), 0)
        self.btn_map_link = QPushButton("Polacz z baza materialow", mapping_right)
        self.btn_map_new = QPushButton("Utworz nowy material", mapping_right)
        self.btn_map_recalc = QPushButton("Przelicz wycene", mapping_right)
        for btn in (self.btn_map_link, self.btn_map_new, self.btn_map_recalc):
            btn.setMinimumHeight(32)
            mapping_right_lay.addWidget(btn, 0)
        mapping_right_lay.addStretch(1)
        lay_mapping.addWidget(mapping_right, 2)

        tab_cutting = QWidget(self.tabs)
        lay_cutting = QVBoxLayout(tab_cutting)
        lay_cutting.setContentsMargins(8, 8, 8, 8)
        lay_cutting.setSpacing(8)
        lay_cutting.addWidget(QLabel("Krok 5: rozkroj / wynik z GiB Lab (realne plyty i odpad).", tab_cutting), 0)
        cut_head = QHBoxLayout()
        self.lab_cut_theory = QLabel("Teoria: 0.00 m2 | 0.00 mb", tab_cutting)
        self.lab_cut_real = QLabel("Realnie: brak danych", tab_cutting)
        self.lab_cut_diff = QLabel("Roznica kosztu: 0.00 zl", tab_cutting)
        cut_head.addWidget(self.lab_cut_theory, 0)
        cut_head.addWidget(self.lab_cut_real, 0)
        cut_head.addWidget(self.lab_cut_diff, 0)
        cut_head.addStretch(1)
        lay_cutting.addLayout(cut_head)
        self.tbl_cutting = QTableWidget(0, 8, tab_cutting)
        self.tbl_cutting.setHorizontalHeaderLabels(
            [
                "Material",
                "Format arkusza",
                "Ilosc plyt",
                "Pow. czesci [m2]",
                "Odpad [m2]",
                "Wykorzystanie [%]",
                "Koszt realny [zl]",
                "Roznica vs teoria [zl]",
            ]
        )
        self.tbl_cutting.verticalHeader().setVisible(False)
        self.tbl_cutting.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_cutting.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ch = self.tbl_cutting.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ch.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for col in (2, 3, 4, 5, 6, 7):
            ch.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        lay_cutting.addWidget(self.tbl_cutting, 1)

        self.tabs.addTab(tab_import, "1. Import")
        self.tabs.addTab(tab_control, "2. Kontrola")
        self.tabs.addTab(tab_mapping, "3. Mapowanie")
        self.tabs.addTab(tab_pricing, "4. Wycena")
        self.tabs.addTab(tab_cutting, "5. Rozkroj")

        self.btn_import.clicked.connect(self._on_import_file)
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        self.btn_open_giblab.clicked.connect(self._on_open_in_giblab)
        self.btn_load_gib_result.clicked.connect(self._on_load_gib_result)
        self.btn_refresh.clicked.connect(self._on_refresh)
        self.btn_cancel.clicked.connect(self._on_cancel_import)
        self.btn_go_mapping.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_transfer.clicked.connect(self._on_transfer)
        self.btn_save_mapping.clicked.connect(self._on_save_mapping)
        self.ed_filter.textChanged.connect(self._refresh_control_table)
        self.cb_control_section.currentIndexChanged.connect(self._refresh_control_table)
        self.cb_pricing_group.currentIndexChanged.connect(self._refresh_pricing_table)
        self.btn_map_recalc.clicked.connect(self._refresh_pricing_table)
        self.btn_map_link.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_map_new.clicked.connect(
            lambda: QMessageBox.information(self, "Nowy material", "Utworz material w bazie i wybierz go w mapowaniu.")
        )

    @property
    def created_entry(self) -> dict[str, Any] | None:
        return dict(self._created_entry) if isinstance(self._created_entry, dict) else None

    @property
    def created_assembly(self) -> dict[str, Any] | None:
        return dict(self._created_assembly) if isinstance(self._created_assembly, dict) else None

    @property
    def transfer_target(self) -> str:
        return str(self._transfer_target or "quick")

    def _on_import_file(self) -> None:
        start_dir = str(self._loaded_path.parent) if self._loaded_path else str(Path.cwd())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik projektu 3D",
            start_dir,
            "Pliki projektu (*.project);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        self._load_project(Path(file_path))

    def _on_open_folder(self) -> None:
        if self._loaded_path is not None and self._loaded_path.parent.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._loaded_path.parent)))
            return
        default_dir = Path.cwd() / "Export z 3DConstructor"
        if default_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(default_dir)))
            return
        QMessageBox.information(self, "Folder importu", "Brak folderu importu do otwarcia.")

    def _on_open_in_giblab(self) -> None:
        if self._loaded_path is None or not self._loaded_path.exists():
            QMessageBox.information(self, "GiB Lab", "Najpierw zaladuj plik .project.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._loaded_path)))

    def _on_load_gib_result(self) -> None:
        start_dir = str(self._loaded_path.parent) if self._loaded_path else str(Path.cwd())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wczytaj wynik z GiB Lab",
            start_dir,
            "Pliki projektu (*.project);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            giblab_result = build_giblab_result_from_project_file(path, self._pricing_rows_cache)
        except Exception as exc:
            QMessageBox.critical(self, "Blad", f"Nie mozna odczytac wyniku GiB Lab.\n\n{exc}")
            return
        self._giblab_result = giblab_result
        self._giblab_result_path = path
        if self._project_model is not None:
            attach_giblab_result(self._project_model, giblab_result)

        material_amount = float(giblab_result.difference_vs_theory.get("theory_material_total", 0.0) or 0.0) + float(
            giblab_result.difference_vs_theory.get("material_total", 0.0) or 0.0
        )
        parts_amount = float(giblab_result.difference_vs_theory.get("parts_amount", 0.0) or 0.0)
        waste_amount = float(giblab_result.difference_vs_theory.get("waste_amount", 0.0) or 0.0)
        utilization = float(giblab_result.difference_vs_theory.get("utilization_pct", 0.0) or 0.0)
        diff_cost = float(giblab_result.difference_vs_theory.get("material_total", 0.0) or 0.0)

        self.tbl_cutting.setRowCount(0)
        self.tbl_cutting.insertRow(0)
        values = [
            "GiB Lab (z pliku)",
            "-",
            "1",
            f"{parts_amount:.3f}",
            f"{waste_amount:.3f}",
            f"{utilization:.2f}",
            f"{real_cost:.2f}",
            f"{diff_cost:.2f}",
        ]
        for col, value in enumerate(values):
            it = QTableWidgetItem(str(value))
            if col >= 2:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_cutting.setItem(0, col, it)

        self.lab_cut_real.setText(
            f"Realnie: czesci {parts_amount:.3f} m2 | odpad {waste_amount:.3f} m2 | wykorzystanie {utilization:.2f}%"
        )
        self.lab_cut_diff.setText(f"Roznica kosztu: {diff_cost:.2f} zl")
        self.tabs.setCurrentIndex(4)

    def _on_refresh(self) -> None:
        if self._loaded_path is None:
            return
        self._load_project(self._loaded_path)

    def _on_cancel_import(self) -> None:
        self._import_data = None
        self._project_model = None
        self._giblab_result = None
        self._giblab_result_path = None
        self._loaded_path = None
        self._created_entry = None
        self._created_assembly = None
        self._pricing_rows_cache = []
        self.lab_file.setText("Plik: [brak]")
        self.lab_preview_module.setText("-")
        self.lab_preview_dims.setText("-")
        self.lab_preview_materials.setText("-")
        self.lab_preview_cost.setText("0.00 zl")
        for label in self._summary_labels.values():
            label.setText("-")
        self.tbl_control.setRowCount(0)
        self.tbl_mapping.setRowCount(0)
        self.tbl_pricing.setRowCount(0)
        self.pb_readiness.setValue(0)
        self.lab_ready_pct.setText("0%")
        self.lab_ready_formatki.setText("Formatki: -")
        self.lab_ready_fronty.setText("Fronty: -")
        self.lab_ready_okucia.setText("Okucia: -")
        self.lab_ready_materials.setText("Materialy: -")
        self.lab_sum_material_card.setText("Materialy: 0.00 zl")
        self.lab_sum_edge_card.setText("Okleina: 0.00 zl")
        self.lab_sum_labor_card.setText("Robocizna: 0.00 zl")
        self.lab_sum_total_card.setText("Razem: 0.00 zl")
        self.lab_kpi_elements.setText("0")
        self.lab_kpi_area.setText("0.00 m2")
        self.lab_kpi_edge.setText("0.00 mb")
        self.lab_kpi_mapping.setText("0%")
        self.lab_cut_theory.setText("Teoria: 0.00 m2 | 0.00 mb")
        self.lab_cut_real.setText("Realnie: brak danych")
        self.lab_cut_diff.setText("Roznica kosztu: 0.00 zl")
        self.tbl_cutting.setRowCount(0)
        self.lab_totals.setText("Materialy: 0.00 zl | Okleina: 0.00 zl | Robocizna: 0.00 zl | Razem: 0.00 zl")

    @staticmethod
    def _apply_status_style(item: QTableWidgetItem, status: str) -> None:
        token = str(status or "").strip().lower()
        if token in {"ok", "polaczono"}:
            item.setBackground(QColor("#dcfce7"))
        elif token in {"wymaga decyzji", "do mapowania", "nie znaleziono"}:
            item.setBackground(QColor("#fef3c7"))
        elif token in {"brak danych", "pominieto"}:
            item.setBackground(QColor("#e5e7eb"))

    def _load_project(self, path: Path) -> None:
        try:
            parsed = parse_3dc_project_for_quote_import(path)
        except (Constructor3dcQuoteImportError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Blad importu", str(exc))
            return
        self._loaded_path = path
        self._import_data = parsed
        self._giblab_result = None
        self._giblab_result_path = None
        self.lab_file.setText(f"Plik: {path}")
        self._refresh_summary()
        self._refresh_mapping_table()
        self._refresh_control_table()
        self._refresh_pricing_table()

    def _refresh_summary(self) -> None:
        summary = self._import_data.summary if self._import_data is not None else None
        if summary is None:
            return
        self._summary_labels["project_name"].setText(summary.project_name)
        self._summary_labels["module_name"].setText(summary.module_name or "-")
        self._summary_labels["dims"].setText(
            f"{summary.module_length_mm:.0f} x {summary.module_width_mm:.0f} x {summary.module_height_mm:.0f} mm"
        )
        self._summary_labels["counts"].setText(
            " | ".join(
                [
                    f"Formatki: {summary.formatki_count}",
                    f"Fronty: {summary.fronty_count}",
                    f"Okucia: {summary.okucia_count}",
                    f"Laczniki: {summary.laczniki_count}",
                    f"Operacje: {summary.operations_count}",
                ]
            )
        )
        self._summary_labels["area"].setText(f"{summary.total_area_m2:.3f}")
        self._summary_labels["edge"].setText(f"{summary.total_edgeband_mb:.3f}")
        total_items = (
            int(summary.formatki_count)
            + int(summary.fronty_count)
            + int(summary.okucia_count)
            + int(summary.laczniki_count)
            + int(summary.operations_count)
        )
        self.lab_kpi_elements.setText(str(total_items))
        self.lab_kpi_area.setText(f"{summary.total_area_m2:.2f} m2")
        self.lab_kpi_edge.setText(f"{summary.total_edgeband_mb:.2f} mb")
        status_txt = str(summary.import_status or "OK")
        if status_txt.strip().lower() == "wymaga mapowania":
            status_txt = "Do mapowania"
        self._summary_labels["status"].setText(status_txt)

    def _material_choice_items(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = [("", "[nie mapuj]")]
        for mat in self._catalog.list_materials():
            out.append((f"material:{mat.key}", f"{mat.key} | {mat.name_pl}"))
        return out

    def _edgeband_choice_items(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = [("", "[nie mapuj]")]
        for edge in self._catalog.list_edgebands():
            out.append((f"edgeband:{edge.key}", f"{edge.key} | {edge.name_pl}"))
        return out

    def _hardware_choice_items(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = [("", "[nie mapuj]")]
        for hw in self._catalog.list_hardware():
            out.append((f"hardware:{hw.key}", f"{hw.key} | {hw.name_pl}"))
        return out

    def _operation_choice_items(self) -> list[tuple[str, str]]:
        return [("", "[nie mapuj]"), ("operation:custom", "Usluga wewnetrzna")]

    def _mapping_section_key(self, kind: str) -> str:
        if kind == "material":
            return "material_map"
        if kind == "edgeband":
            return "edgeband_map"
        if kind == "hardware":
            return "hardware_map"
        return "operation_map"

    @staticmethod
    def _guess_mapping_value(import_name: str, choices: list[tuple[str, str]]) -> str:
        token = str(import_name or "").strip().lower()
        if not token:
            return ""
        for value, label in choices:
            if not value:
                continue
            if token in str(label or "").strip().lower():
                return str(value)
        return ""

    @staticmethod
    def _edge_map_from_desc(desc: str) -> dict[str, str]:
        out: dict[str, str] = {}
        raw = str(desc or "").strip()
        if not raw:
            return out
        for token in raw.split(","):
            part = str(token or "").strip()
            if ":" not in part:
                continue
            side, label = part.split(":", 1)
            side_key = str(side or "").strip().upper()
            label_val = str(label or "").strip()
            if side_key in {"L", "R", "T", "B"} and label_val:
                out[side_key] = label_val
        return out

    def _refresh_mapping_table(self) -> None:
        self.tbl_mapping.setRowCount(0)
        self._mapping_combo_by_row.clear()
        self._mapping_key_by_row.clear()
        if self._import_data is None:
            return
        seen: set[tuple[str, str]] = set()
        mapping_rows: list[tuple[str, str]] = []
        for row in self._import_data.control_rows:
            material_text = str(row.material_import or "").strip()
            if material_text:
                if row.section in {"Formatka", "Front"}:
                    key = ("material", material_text)
                elif row.section in {"Okucie", "Lacznik"}:
                    key = ("hardware", material_text)
                else:
                    key = ("operation", material_text)
                if key not in seen:
                    seen.add(key)
                    mapping_rows.append(key)
            edge_desc = self._edge_map_from_desc(row.edgeband_desc)
            for edge_name in edge_desc.values():
                key = ("edgeband", edge_name)
                if key not in seen:
                    seen.add(key)
                    mapping_rows.append(key)

        self._suspend_mapping_events = True
        try:
            for kind, import_name in mapping_rows:
                row_idx = self.tbl_mapping.rowCount()
                self.tbl_mapping.insertRow(row_idx)
                self.tbl_mapping.setItem(row_idx, 0, QTableWidgetItem(kind))
                self.tbl_mapping.setItem(row_idx, 1, QTableWidgetItem(import_name))
                combo = QComboBox(self.tbl_mapping)
                if kind == "material":
                    choices = self._material_choice_items()
                elif kind == "edgeband":
                    choices = self._edgeband_choice_items()
                elif kind == "hardware":
                    choices = self._hardware_choice_items()
                else:
                    choices = self._operation_choice_items()
                for value, label in choices:
                    combo.addItem(label, value)
                section_key = self._mapping_section_key(kind)
                map_key = f"{kind}:{import_name}"
                mapped_value = str(self._mapping.get(section_key, {}).get(map_key, "") or "")
                if not mapped_value:
                    mapped_value = self._guess_mapping_value(import_name, choices)
                idx = combo.findData(mapped_value)
                if idx < 0:
                    idx = 0
                combo.setCurrentIndex(idx)
                combo.currentIndexChanged.connect(self._on_mapping_changed)
                self.tbl_mapping.setCellWidget(row_idx, 2, combo)
                status_text = "Polaczono" if mapped_value else "Wymaga decyzji"
                status_item = QTableWidgetItem(status_text)
                self.tbl_mapping.setItem(row_idx, 3, status_item)
                self._apply_status_style(status_item, status_text)
                self._mapping_combo_by_row[row_idx] = combo
                self._mapping_key_by_row[row_idx] = (kind, import_name)
        finally:
            self._suspend_mapping_events = False
        mapped = 0
        total = self.tbl_mapping.rowCount()
        for row_idx in range(total):
            st = self.tbl_mapping.item(row_idx, 3)
            token = str(st.text() if st is not None else "").strip().lower()
            if token in {"polaczono", "ok"}:
                mapped += 1
        pct = int(round((mapped * 100.0) / total)) if total > 0 else 0
        self.lab_kpi_mapping.setText(f"{pct}%")

    def _on_mapping_changed(self, _index: int) -> None:
        if self._suspend_mapping_events:
            return
        for row_idx, combo in self._mapping_combo_by_row.items():
            key = self._mapping_key_by_row.get(row_idx)
            if key is None:
                continue
            kind, import_name = key
            section_key = self._mapping_section_key(kind)
            map_key = f"{kind}:{import_name}"
            value = str(combo.currentData() or "").strip()
            section = self._mapping.setdefault(section_key, {})
            if value:
                section[map_key] = value
                status_text = "Polaczono"
            else:
                section.pop(map_key, None)
                status_text = "Wymaga decyzji"
            status_item = QTableWidgetItem(status_text)
            self.tbl_mapping.setItem(row_idx, 3, status_item)
            self._apply_status_style(status_item, status_text)
        mapped = 0
        total = self.tbl_mapping.rowCount()
        for row_idx in range(total):
            st = self.tbl_mapping.item(row_idx, 3)
            token = str(st.text() if st is not None else "").strip().lower()
            if token in {"polaczono", "ok"}:
                mapped += 1
        pct = int(round((mapped * 100.0) / total)) if total > 0 else 0
        self.lab_kpi_mapping.setText(f"{pct}%")
        self._refresh_control_table()
        self._refresh_pricing_table()

    def _mapped_label(self, row: ImportControlRow) -> str:
        material_text = str(row.material_import or "").strip()
        if not material_text:
            return ""
        if row.section in {"Formatka", "Front"}:
            section_key = "material_map"
            map_key = f"material:{material_text}"
        elif row.section in {"Okucie", "Lacznik"}:
            section_key = "hardware_map"
            map_key = f"hardware:{material_text}"
        else:
            section_key = "operation_map"
            map_key = f"operation:{material_text}"
        return str(self._mapping.get(section_key, {}).get(map_key, "") or "")

    def _mapped_edge_label(self, edge_import_label: str) -> str:
        key = f"edgeband:{edge_import_label}"
        return str(self._mapping.get("edgeband_map", {}).get(key, "") or "")

    def _mapping_status_for_row(self, row: ImportControlRow) -> str:
        if row.section not in {"Formatka", "Front", "Okucie", "Lacznik", "Operacja"}:
            return "Pominieto"
        material_text = str(row.material_import or "").strip()
        if not material_text and row.section != "Operacja":
            return "Brak danych"
        if row.section == "Operacja":
            return "OK" if self._mapped_label(row) else "Do mapowania"
        status_material = bool(self._mapped_label(row))
        if row.section in {"Formatka", "Front"}:
            edge_map = self._edge_map_from_desc(row.edgeband_desc)
            all_edges_mapped = True
            for edge_name in edge_map.values():
                if not self._mapped_edge_label(edge_name):
                    all_edges_mapped = False
                    break
            return "OK" if status_material and all_edges_mapped else "Do mapowania"
        return "OK" if status_material else "Do mapowania"

    def _refresh_control_table(self) -> None:
        self.tbl_control.setRowCount(0)
        if self._import_data is None:
            return
        query = str(self.ed_filter.text() or "").strip().lower()
        section_filter = str(self.cb_control_section.currentData() or "").strip()
        for row in self._import_data.control_rows:
            if section_filter and row.section != section_filter:
                continue
            hay = " ".join([row.section, row.code, row.name, row.material_import, row.edgeband_desc, row.source_id]).lower()
            if query and query not in hay:
                continue
            row_idx = self.tbl_control.rowCount()
            self.tbl_control.insertRow(row_idx)
            status = self._mapping_status_for_row(row)
            values = [
                row.section,
                row.code,
                row.name,
                f"{row.qty:.3f}".rstrip("0").rstrip("."),
                f"{row.length_mm:.2f}".rstrip("0").rstrip("."),
                f"{row.width_mm:.2f}".rstrip("0").rstrip("."),
                f"{row.thickness_mm:.2f}".rstrip("0").rstrip("."),
                row.material_import,
                row.edgeband_desc,
                f"{row.edgeband_mb:.3f}",
                f"{row.area_m2:.3f}",
                status,
                row.source,
                row.source_id,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.tbl_control.setItem(row_idx, col, item)
                if col == 11:
                    self._apply_status_style(item, status)

    def _mapped_material_price(self, row: ImportControlRow) -> float:
        mapped = self._mapped_label(row)
        if mapped.startswith("material:"):
            key = mapped.split(":", 1)[1]
            return float(self._catalog.material_price_per_m2(key, 0.0))
        if row.unit_cost > 0 and row.area_m2 > 0:
            return float(row.unit_cost)
        return 0.0

    def _mapped_edgeband_price(self, edge_import_label: str) -> float:
        mapped = self._mapped_edge_label(edge_import_label)
        if mapped.startswith("edgeband:"):
            key = mapped.split(":", 1)[1]
            return float(self._catalog.edgeband_price_per_m(key, 0.0))
        return 0.0

    @staticmethod
    def _edge_length_mm_for_side(side: str, length_mm: float, width_mm: float) -> float:
        if side in {"L", "R"}:
            return max(0.0, length_mm)
        if side in {"T", "B"}:
            return max(0.0, width_mm)
        return 0.0

    def _build_pricing_row(self, row: ImportControlRow) -> dict[str, Any]:
        group = "Korpus"
        if row.section == "Front":
            group = "Fronty"
        elif row.section == "Okucie":
            group = "Okucia"
        elif row.section == "Lacznik":
            group = "Laczniki"
        elif row.section == "Operacja":
            group = "Operacje"

        edges = self._edge_map_from_desc(row.edgeband_desc)
        edge_l = edges.get("L", "-")
        edge_r = edges.get("R", "-")
        edge_t = edges.get("T", "-")
        edge_b = edges.get("B", "-")

        edge_mb_total = 0.0
        edge_cost = 0.0
        for side, name in edges.items():
            side_mm = self._edge_length_mm_for_side(side, row.length_mm, row.width_mm)
            side_mb = (side_mm * max(0.0, row.qty)) / 1000.0
            edge_mb_total += side_mb
            edge_cost += side_mb * self._mapped_edgeband_price(name)

        material_price = 0.0
        material_cost = 0.0
        labor_cost = 0.0
        extra_cost = 0.0

        if row.section in {"Formatka", "Front"}:
            material_price = self._mapped_material_price(row)
            material_cost = row.area_m2 * material_price
        elif row.section in {"Okucie", "Lacznik"}:
            extra_cost = row.qty * row.unit_cost
        else:
            labor_cost = row.qty * row.unit_cost

        total = material_cost + edge_cost + labor_cost + extra_cost

        return {
            "section": row.section,
            "group": group,
            "name": row.name,
            "source": f"Import 3D / {self._import_data.summary.project_name}",
            "material": row.material_import,
            "thickness": row.thickness_mm,
            "length": row.length_mm,
            "width": row.width_mm,
            "qty": row.qty,
            "edge_l": edge_l,
            "edge_r": edge_r,
            "edge_t": edge_t,
            "edge_b": edge_b,
            "edge_mb": edge_mb_total,
            "area_m2": row.area_m2,
            "material_price": material_price,
            "edge_price": (edge_cost / edge_mb_total) if edge_mb_total > 0 else 0.0,
            "material_cost": material_cost,
            "edge_cost": edge_cost,
            "labor_cost": labor_cost,
            "extra_cost": extra_cost,
            "sum": total,
            "note": row.code,
        }

    @staticmethod
    def _fmt(v: float, decimals: int = 2) -> str:
        return f"{float(v):.{decimals}f}"

    def _refresh_pricing_table(self) -> None:
        self.tbl_pricing.setRowCount(0)
        self._pricing_rows_cache = []
        if self._import_data is None:
            self.lab_preview_module.setText("-")
            self.lab_preview_dims.setText("-")
            self.lab_preview_materials.setText("-")
            self.lab_preview_cost.setText("0.00 zl")
            self.pb_readiness.setValue(0)
            self.lab_ready_pct.setText("0%")
            self.lab_ready_formatki.setText("Formatki: -")
            self.lab_ready_fronty.setText("Fronty: -")
            self.lab_ready_okucia.setText("Okucia: -")
            self.lab_ready_materials.setText("Materialy: -")
            self.lab_sum_material_card.setText("Materialy: 0.00 zl")
            self.lab_sum_edge_card.setText("Okleina: 0.00 zl")
            self.lab_sum_labor_card.setText("Robocizna: 0.00 zl")
            self.lab_sum_total_card.setText("Razem: 0.00 zl")
            self.lab_cut_theory.setText("Teoria: 0.00 m2 | 0.00 mb")
            self._project_model = None
            return

        group_filter = str(self.cb_pricing_group.currentData() or "").strip()
        grouped: dict[str, list[dict[str, Any]]] = {}

        total_material = 0.0
        total_edge = 0.0
        total_labor = 0.0
        total_extra = 0.0

        for row in self._import_data.control_rows:
            packed = self._build_pricing_row(row)
            self._pricing_rows_cache.append(packed)
            grouped.setdefault(str(packed["group"]), []).append(packed)
            total_material += float(packed["material_cost"])
            total_edge += float(packed["edge_cost"])
            total_labor += float(packed["labor_cost"])
            total_extra += float(packed["extra_cost"])

        total_value = total_material + total_edge + total_labor + total_extra
        self.lab_totals.setText(
            f"Materialy: {total_material:.2f} zl | Okleina: {total_edge:.2f} zl | "
            f"Robocizna: {total_labor:.2f} zl | Razem: {total_value:.2f} zl"
        )
        self.lab_sum_material_card.setText(f"Materialy: {total_material:.2f} zl")
        self.lab_sum_edge_card.setText(f"Okleina: {total_edge:.2f} zl")
        self.lab_sum_labor_card.setText(f"Robocizna: {total_labor:.2f} zl")
        self.lab_sum_total_card.setText(f"Razem: {total_value:.2f} zl")

        summary = self._import_data.summary
        self.lab_cut_theory.setText(f"Teoria: {summary.total_area_m2:.3f} m2 | {summary.total_edgeband_mb:.3f} mb")
        materials = sorted({str(r.material_import or "").strip() for r in self._import_data.control_rows if str(r.material_import or "").strip()})
        self.lab_preview_module.setText(summary.module_name or summary.project_name)
        self.lab_preview_dims.setText(
            f"{summary.module_length_mm:.0f} x {summary.module_width_mm:.0f} x {summary.module_height_mm:.0f} mm"
        )
        self.lab_preview_materials.setText(", ".join(materials[:6]) + ("..." if len(materials) > 6 else ""))
        self.lab_preview_cost.setText(f"{total_value:.2f} zl")
        map_total = self.tbl_mapping.rowCount()
        mapped = 0
        for row_idx in range(map_total):
            st = self.tbl_mapping.item(row_idx, 3)
            token = str(st.text() if st is not None else "").strip().lower()
            if token in {"polaczono", "ok"}:
                mapped += 1
        ready_pct = int(round((mapped * 100.0) / map_total)) if map_total > 0 else 100
        self.pb_readiness.setValue(ready_pct)
        self.lab_ready_pct.setText(f"{ready_pct}%")
        self.lab_ready_formatki.setText(f"Formatki: {summary.formatki_count}")
        self.lab_ready_fronty.setText(f"Fronty: {summary.fronty_count}")
        self.lab_ready_okucia.setText(f"Okucia/Laczniki: {summary.okucia_count + summary.laczniki_count}")
        self.lab_ready_materials.setText(f"Materialy do mapowania: {max(0, map_total - mapped)}")
        if self._loaded_path is not None and self._import_data is not None:
            self._project_model = build_import_3d_project_model(
                self._import_data,
                self._pricing_rows_cache,
                self._mapping,
                source_path=str(self._loaded_path),
            )
            if self._giblab_result is not None:
                attach_giblab_result(self._project_model, self._giblab_result)

        order = ("Korpus", "Fronty", "Okucia", "Laczniki", "Operacje")
        for group in order:
            rows = grouped.get(group, [])
            if not rows:
                continue
            if group_filter and group != group_filter:
                continue

            subtotal = sum(float(r.get("sum", 0.0) or 0.0) for r in rows)
            header_row = self.tbl_pricing.rowCount()
            self.tbl_pricing.insertRow(header_row)
            hdr = QTableWidgetItem(f"[{group}]")
            hdr.setBackground(QColor("#e5e7eb"))
            self.tbl_pricing.setItem(header_row, 0, hdr)
            sub_item = QTableWidgetItem(f"{subtotal:.2f}")
            sub_item.setBackground(QColor("#e5e7eb"))
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_pricing.setItem(header_row, 20, sub_item)

            for packed in rows:
                row_idx = self.tbl_pricing.rowCount()
                self.tbl_pricing.insertRow(row_idx)
                values = [
                    packed["group"],
                    packed["name"],
                    packed["source"],
                    packed["material"],
                    self._fmt(packed["thickness"], 1) if packed["thickness"] else "-",
                    self._fmt(packed["length"], 1) if packed["length"] else "-",
                    self._fmt(packed["width"], 1) if packed["width"] else "-",
                    self._fmt(packed["qty"], 3).rstrip("0").rstrip("."),
                    packed["edge_l"],
                    packed["edge_r"],
                    packed["edge_t"],
                    packed["edge_b"],
                    self._fmt(packed["edge_mb"], 3),
                    self._fmt(packed["area_m2"], 3),
                    self._fmt(packed["material_price"], 2),
                    self._fmt(packed["edge_price"], 2),
                    self._fmt(packed["material_cost"], 2),
                    self._fmt(packed["edge_cost"], 2),
                    self._fmt(packed["labor_cost"], 2),
                    self._fmt(packed["extra_cost"], 2),
                    self._fmt(packed["sum"], 2),
                    packed["note"],
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if col in (4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.tbl_pricing.setItem(row_idx, col, item)

    def get_project_model(self) -> ProjectModel | None:
        return self._project_model

    def _on_save_mapping(self) -> None:
        try:
            self._mapping_store.save(self._mapping)
        except Exception as exc:
            QMessageBox.critical(self, "Blad zapisu", f"Nie udalo sie zapisac mapowania.\n\n{exc}")
            return
        QMessageBox.information(self, "Mapowanie", "Mapowanie materialow zostalo zapisane.")

    def _build_quick_quote_entry(self) -> dict[str, Any] | None:
        if self._import_data is None:
            return None
        group_totals: dict[str, float] = {}
        total = 0.0
        for row in self._pricing_rows_cache:
            group = str(row.get("group", "") or "").strip()
            value = float(row.get("sum", 0.0) or 0.0)
            group_totals[group] = group_totals.get(group, 0.0) + value
            total += value
        sections = []
        section_idx = 1
        for group, value in group_totals.items():
            sections.append({"id": f"IMP{section_idx:02d}", "title": group, "price": f"{value:.2f} zl"})
            section_idx += 1
        quote_id = f"QIMP_{self._import_data.summary.project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            "id": quote_id,
            "title": f"Import 3D: {self._import_data.summary.project_name}",
            "client": "",
            "price": f"{total:.2f} zl",
            "discount_pct": "0.00%",
            "vat": "23%",
            "margin": "0.00%",
            "order_code": "",
            "sections": sections,
        }

    def _build_assembly_payload(self) -> dict[str, Any] | None:
        if self._import_data is None:
            return None
        summary = self._import_data.summary
        total = sum(float(row.get("sum", 0.0) or 0.0) for row in self._pricing_rows_cache)
        return {
            "name": f"IMP 3D | {summary.project_name}",
            "order_name": f"IMP3D-{summary.project_name}",
            "client_name": "",
            "wall_name": "",
            "worker_name": "",
            "width_mm": float(summary.module_length_mm or 3000.0),
            "height_mm": float(summary.module_height_mm or 2500.0),
            "depth_mm": float(summary.module_width_mm or 560.0),
            "gap_mm": 0.0,
            "material_profile_key": "STD_WHITE",
            "force_hardware_from_profile": True,
            "labor_cost_pln": float(total),
            "transport_cost_pln": 0.0,
            "montage_cost_pln": 0.0,
            "margin_percent": 0.0,
            "items": [],
        }

    def _on_transfer(self) -> None:
        entry = self._build_quick_quote_entry()
        if entry is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw zaimportuj plik .project.")
            return

        total_val = sum(float(row.get("sum", 0.0) or 0.0) for row in self._pricing_rows_cache)
        summary = self._import_data.summary if self._import_data is not None else None
        module_name = summary.module_name if summary is not None else "-"
        dims = (
            f"{summary.module_length_mm:.0f} x {summary.module_width_mm:.0f} x {summary.module_height_mm:.0f} mm"
            if summary is not None
            else "-"
        )
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setWindowTitle("Potwierdzenie wczytania")
        confirm.setText("Czy na pewno wczytac modul do wyceny?")
        confirm.setInformativeText(
            f"Modul: {module_name}\n"
            f"Wymiary: {dims}\n"
            f"Pozycje: {len(self._pricing_rows_cache)}\n"
            f"Cena laczna: {total_val:.2f} zl"
        )
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.Yes)
        if confirm.exec() != int(QMessageBox.StandardButton.Yes):
            return

        self._transfer_target = str(self.cb_target.currentData() or "quick")
        self._created_entry = entry
        self._created_assembly = self._build_assembly_payload()
        self.accept()
