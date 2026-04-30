from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.domain.instruction_models import InstructionCardDef
from src.storage.instruction_store_json import InstructionStoreJson


@dataclass(frozen=True)
class _VisualLaunchSpec:
    title: str
    subtitle: str
    accent: str
    target_tab: str
    hint: str


@dataclass(frozen=True)
class _ScreenAsset:
    name: str
    pack: str
    path: Path


class _HeroCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #0f172a;
                border: 1px solid #e8efff;
                border-radius: 24px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(6)

        title = QLabel("GRAFIKA / BIBLIOTEKA WIZUALNA")
        title.setStyleSheet("color:#ffffff;font-size:28px;font-weight:900;")
        text_col.addWidget(title)

        subtitle = QLabel(
            "Jedno miejsce na instrukcje, podglady ekranow, boty, style UI i materialy do konsultacji wizualnych."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#cbd5e1;font-size:13px;")
        text_col.addWidget(subtitle)

        chip_row = QHBoxLayout()
        chip_row.setContentsMargins(0, 2, 0, 0)
        chip_row.setSpacing(8)
        for text, bg, fg in (
            ("Instrukcje", "#dbeafe", "#1d4ed8"),
            ("Ekrany", "#dcfce7", "#166534"),
            ("Boty", "#ede9fe", "#6d28d9"),
            ("Motywy", "#ffedd5", "#c2410c"),
        ):
            chip = QLabel(text)
            chip.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:999px; padding:5px 11px; "
                "font-size:12px; font-weight:800;"
            )
            chip_row.addWidget(chip)
        chip_row.addStretch(1)
        text_col.addLayout(chip_row)
        layout.addLayout(text_col, 3)

        stats = QVBoxLayout()
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(8)
        for label, value, color in (
            ("Instrukcje", "2+", "#60a5fa"),
            ("Ekrany", "6", "#34d399"),
            ("Boty", "5", "#a78bfa"),
        ):
            card = QFrame(); card.setProperty("uiCard", True)
            card.setStyleSheet("QFrame{background:#111827;border:1px solid #243041;border-radius:16px;}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(2)
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color:{color};font-size:26px;font-weight:900;")
            card_layout.addWidget(value_label)
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color:#cbd5e1;font-size:12px;font-weight:700;")
            card_layout.addWidget(label_widget)
            stats.addWidget(card)
        layout.addLayout(stats, 1)


class _VisualLaunchCard(QFrame):
    def __init__(self, spec: _VisualLaunchSpec, on_open: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 18px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QFrame()
        header.setStyleSheet(f"QFrame{{background:{spec.accent};border-radius:14px;}}")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(3)

        title = QLabel(spec.title)
        title.setStyleSheet("color:#ffffff;font-size:15px;font-weight:800;")
        subtitle = QLabel(spec.subtitle)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#e2e8f0;font-size:11px;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        hint = QLabel(spec.hint)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#94a3b8;font-size:12px;")
        layout.addWidget(hint)

        btn = QPushButton("Otworz ekran")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton{background:#0f172a;color:#ffffff;font-weight:800;padding:8px 12px;border-radius:12px;}"
            "QPushButton:hover{background:#1e293b;}"
        )
        btn.clicked.connect(lambda _checked=False: on_open(spec.target_tab))
        layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)


class _ScreenThumbCard(QFrame):
    def __init__(self, asset: _ScreenAsset, on_open: Callable[[Path], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 16px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)

        thumb = QLabel(self)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setMinimumHeight(132)
        thumb.setStyleSheet("background:#0f172a;border-radius:10px;")
        pixmap = QPixmap(str(asset.path))
        if pixmap.isNull():
            thumb.setText("Brak miniatury")
            thumb.setStyleSheet("background:#e2e8f0;color:#64748b;border-radius:10px;font-size:11px;")
        else:
            thumb.setPixmap(
                pixmap.scaled(
                    260,
                    132,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(thumb)

        file_name = QLabel(asset.name)
        file_name.setWordWrap(True)
        file_name.setStyleSheet("color:#0f172a;font-size:12px;font-weight:800;")
        layout.addWidget(file_name)

        pack = QLabel(asset.pack)
        pack.setStyleSheet(
            "background:#eef2ff;color:#3730a3;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:800;"
        )
        layout.addWidget(pack, 0, Qt.AlignmentFlag.AlignLeft)

        btn = QPushButton("Otworz plik")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton{background:#1d4ed8;color:#ffffff;font-weight:800;padding:7px 11px;border-radius:10px;}"
            "QPushButton:hover{background:#1e40af;}"
        )
        btn.clicked.connect(lambda _checked=False: on_open(asset.path))
        layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)


class _InstructionCardWidget(QFrame):
    def __init__(self, card: InstructionCardDef, on_open_visual: Callable[[InstructionCardDef], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._card = card
        self._on_open_visual = on_open_visual
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 18px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(3)

        title = QLabel(card.title or "Bez tytulu")
        title.setStyleSheet("color:#0f172a;font-size:16px;font-weight:900;")
        title_col.addWidget(title)

        badge = QLabel((card.category or "ogolne").upper())
        badge.setStyleSheet(
            "background:#dbeafe;color:#1d4ed8;border-radius:999px;padding:4px 10px;font-size:11px;font-weight:800;"
        )
        title_col.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        top.addLayout(title_col, 1)

        visual_badge_text = "Brak wizualizacji"
        if card.visualization_path and Path(card.visualization_path).expanduser().exists():
            visual_badge_text = "Wizualizacja gotowa"
        visual_badge = QLabel(visual_badge_text)
        visual_badge.setStyleSheet(
            "background:#eef2ff;color:#4338ca;border-radius:999px;padding:4px 10px;font-size:11px;font-weight:800;"
        )
        top.addWidget(visual_badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        when = QLabel(f"Kiedy: {card.when_to_use or '-'}")
        when.setWordWrap(True)
        when.setStyleSheet("color:#334155;font-size:12px;font-weight:600;")
        layout.addWidget(when)

        impact = QLabel(f"Wplyw: {card.impact or '-'}")
        impact.setWordWrap(True)
        impact.setStyleSheet("color:#94a3b8;font-size:12px;")
        layout.addWidget(impact)

        steps = QLabel(card.steps or "-")
        steps.setWordWrap(True)
        steps.setStyleSheet(
            "background:transparent;border:1px solid #e2e8f0;border-radius:12px;"
            "padding:10px;color:#334155;font-size:12px;line-height:1.4;"
        )
        layout.addWidget(steps)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        path_text = card.visualization_path or "Brak pliku wizualizacji"
        path_label = QLabel(path_text)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color:#64748b;font-size:11px;")
        footer.addWidget(path_label, 1)

        open_btn = QPushButton("Otworz")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setEnabled(bool(card.visualization_path and Path(card.visualization_path).expanduser().exists()))
        open_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:#ffffff;font-weight:800;padding:7px 11px;border-radius:10px;}"
            "QPushButton:disabled{background:#cbd5e1;color:#64748b;}"
        )
        open_btn.clicked.connect(self._open_visualization)
        footer.addWidget(open_btn, 0)

        layout.addLayout(footer)

    def _open_visualization(self) -> None:
        self._on_open_visual(self._card)


class TabGrafika(QWidget):
    sig_open_tab_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = InstructionStoreJson()
        self._all_cards: list[InstructionCardDef] = []
        self._all_screen_assets: list[_ScreenAsset] = []
        self._screen_specs = self._build_screen_specs()

        self.setStyleSheet(
            """
            QWidget {
                background: #eef2f7;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        root.addWidget(_HeroCard(self))

        content = QHBoxLayout()
        content.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        instruction_panel = self._make_panel()
        instruction_layout = QVBoxLayout(instruction_panel)
        instruction_layout.setContentsMargins(16, 16, 16, 16)
        instruction_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.addWidget(self._make_title("Instrukcje i materialy"))
        header_row.addStretch(1)
        self.btn_refresh = QPushButton("Odswiez")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #cbd5e1;color:#334155;font-weight:700;padding:7px 11px;border-radius:10px;}"
            "QPushButton:hover{background:#eef2f7;}"
        )
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_row.addWidget(self.btn_refresh)
        instruction_layout.addLayout(header_row)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        self.cb_category = QComboBox(self)
        self.cb_category.currentIndexChanged.connect(self._rebuild_instruction_cards)
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po tytule, kroku lub wplywie")
        self.ed_search.textChanged.connect(self._rebuild_instruction_cards)
        filter_row.addWidget(self.cb_category, 0)
        filter_row.addWidget(self.ed_search, 1)
        instruction_layout.addLayout(filter_row)

        self.lab_instruction_count = QLabel("")
        self.lab_instruction_count.setStyleSheet("color:#94a3b8;font-size:12px;font-weight:600;")
        instruction_layout.addWidget(self.lab_instruction_count)

        self._instruction_scroll = QScrollArea(self)
        self._instruction_scroll.setWidgetResizable(True)
        self._instruction_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._instruction_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._instruction_scroll.setMinimumHeight(420)
        self._instruction_cards_host = QWidget(self._instruction_scroll)
        self._instruction_cards_layout = QVBoxLayout(self._instruction_cards_host)
        self._instruction_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._instruction_cards_layout.setSpacing(10)
        self._instruction_scroll.setWidget(self._instruction_cards_host)
        instruction_layout.addWidget(self._instruction_scroll, 1)
        left_col.addWidget(instruction_panel, 1)

        screen_panel = self._make_panel()
        screen_layout = QVBoxLayout(screen_panel)
        screen_layout.setContentsMargins(16, 16, 16, 16)
        screen_layout.setSpacing(10)
        screen_layout.addWidget(self._make_title("Szybkie wejscia do ekranow"))

        screen_grid = QGridLayout()
        screen_grid.setHorizontalSpacing(10)
        screen_grid.setVerticalSpacing(10)
        for idx, spec in enumerate(self._screen_specs):
            card = _VisualLaunchCard(spec, self._open_tab, self)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            screen_grid.addWidget(card, idx // 2, idx % 2)
        screen_layout.addLayout(screen_grid)
        left_col.addWidget(screen_panel)

        gallery_panel = self._make_panel()
        gallery_layout = QVBoxLayout(gallery_panel)
        gallery_layout.setContentsMargins(16, 16, 16, 16)
        gallery_layout.setSpacing(10)

        gallery_head = QHBoxLayout()
        gallery_head.setContentsMargins(0, 0, 0, 0)
        gallery_head.setSpacing(8)
        gallery_head.addWidget(self._make_title("Miniatury screenow"))
        gallery_head.addStretch(1)
        self.btn_open_screens_index = QPushButton("Index MD")
        self.btn_open_screens_index.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_screens_index.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #cbd5e1;color:#334155;font-weight:700;padding:6px 10px;border-radius:10px;}"
            "QPushButton:hover{background:#eef2f7;}"
        )
        self.btn_open_screens_index.clicked.connect(self._open_screens_index)
        gallery_head.addWidget(self.btn_open_screens_index)
        gallery_layout.addLayout(gallery_head)

        gallery_filter_row = QHBoxLayout()
        gallery_filter_row.setContentsMargins(0, 0, 0, 0)
        gallery_filter_row.setSpacing(8)
        self.cb_screen_pack = QComboBox(self)
        self.cb_screen_pack.currentIndexChanged.connect(self._rebuild_screen_gallery)
        self.ed_screen_search = QLineEdit(self)
        self.ed_screen_search.setPlaceholderText("Szukaj po nazwie pliku")
        self.ed_screen_search.textChanged.connect(self._rebuild_screen_gallery)
        gallery_filter_row.addWidget(self.cb_screen_pack, 0)
        gallery_filter_row.addWidget(self.ed_screen_search, 1)
        gallery_layout.addLayout(gallery_filter_row)

        self.lab_screen_count = QLabel("")
        self.lab_screen_count.setStyleSheet("color:#94a3b8;font-size:12px;font-weight:600;")
        gallery_layout.addWidget(self.lab_screen_count)

        self._screen_scroll = QScrollArea(self)
        self._screen_scroll.setWidgetResizable(True)
        self._screen_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._screen_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._screen_scroll.setMinimumHeight(360)
        self._screen_host = QWidget(self._screen_scroll)
        self._screen_grid = QGridLayout(self._screen_host)
        self._screen_grid.setContentsMargins(0, 0, 0, 0)
        self._screen_grid.setHorizontalSpacing(10)
        self._screen_grid.setVerticalSpacing(10)
        self._screen_scroll.setWidget(self._screen_host)
        gallery_layout.addWidget(self._screen_scroll, 1)
        left_col.addWidget(gallery_panel, 1)

        content.addLayout(left_col, 3)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        palette_panel = self._make_panel()
        palette_layout = QVBoxLayout(palette_panel)
        palette_layout.setContentsMargins(16, 16, 16, 16)
        palette_layout.setSpacing(10)
        palette_layout.addWidget(self._make_title("Paleta i statusy"))
        palette_layout.addWidget(self._make_swatches())
        palette_layout.addWidget(self._make_status_legend())
        right_col.addWidget(palette_panel)

        rules_panel = self._make_panel()
        rules_layout = QVBoxLayout(rules_panel)
        rules_layout.setContentsMargins(16, 16, 16, 16)
        rules_layout.setSpacing(8)
        rules_layout.addWidget(self._make_title("Jak tego uzywac"))
        for text in (
            "1. Trzymamy tu wszystkie wizualne elementy programu.",
            "2. Instrukcje z obrazkami i PDF sa widoczne razem z opisem.",
            "3. Z tego miejsca przechodzisz od razu do ekranow roboczych.",
            "4. Jej celem jest porzadek: mniej szukania, wiecej gotowych wzorcow.",
        ):
            line = QLabel(text)
            line.setWordWrap(True)
            line.setStyleSheet("color:#94a3b8;font-size:12px;")
            rules_layout.addWidget(line)
        right_col.addWidget(rules_panel)

        focus_panel = self._make_panel()
        focus_layout = QVBoxLayout(focus_panel)
        focus_layout.setContentsMargins(16, 16, 16, 16)
        focus_layout.setSpacing(8)
        focus_layout.addWidget(self._make_title("Wizualne pakiety"))
        for text, color in (
            ("Onboarding: podglady ekranow i krokow", "#2563eb"),
            ("Boty: mobilne potwierdzenia statusow", "#7c3aed"),
            ("Instrukcje: montaz, okucia i poprawki", "#059669"),
        ):
            row = QFrame()
            row.setStyleSheet("QFrame{background:transparent;border:1px solid #dbe4f0;border-radius:12px;}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(8)
            dot = QLabel("*")
            dot.setStyleSheet(f"color:{color};font-size:16px;font-weight:900;")
            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("color:#1e293b;font-size:12px;font-weight:700;")
            row_layout.addWidget(label, 1)
            focus_layout.addWidget(row)
        right_col.addWidget(focus_panel)

        content.addLayout(right_col, 2)
        root.addLayout(content, 1)

        self.refresh_data()

    def refresh_data(self) -> None:
        cards = list(self._store.list_cards(category="all") or [])
        self._all_cards = cards

        categories = ["all"]
        for card in cards:
            cat = str(card.category or "ogolne").strip().lower()
            if cat and cat not in categories:
                categories.append(cat)

        current = str(self.cb_category.currentData() or "all").strip().lower()
        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem("Wszystkie", "all")
        for cat in sorted(c for c in categories if c != "all"):
            self.cb_category.addItem(cat.capitalize(), cat)
        idx = self.cb_category.findData(current)
        if idx >= 0:
            self.cb_category.setCurrentIndex(idx)
        self.cb_category.blockSignals(False)

        self._rebuild_instruction_cards()
        self._reload_screen_assets()
        self._rebuild_screen_pack_filter()
        self._rebuild_screen_gallery()

    def _rebuild_instruction_cards(self) -> None:
        while self._instruction_cards_layout.count():
            item = self._instruction_cards_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        category = str(self.cb_category.currentData() or "all").strip().lower()
        needle = str(self.ed_search.text() or "").strip().lower()
        filtered: list[InstructionCardDef] = []
        for card in self._all_cards:
            if category not in ("all", "wszystkie") and card.category != category:
                continue
            haystack = " | ".join(
                part for part in (card.title, card.when_to_use, card.impact, card.steps, card.visualization_path) if part
            ).lower()
            if needle and needle not in haystack:
                continue
            filtered.append(card)

        if not filtered:
            empty = QLabel("Brak instrukcji dla wybranego filtra.")
            empty.setStyleSheet("color:#64748b;font-size:12px;font-style:italic;")
            self._instruction_cards_layout.addWidget(empty)
        else:
            for card in filtered:
                widget = _InstructionCardWidget(card, self._open_visual_for_card, self)
                self._instruction_cards_layout.addWidget(widget)

        self._instruction_cards_layout.addStretch(1)
        self.lab_instruction_count.setText(f"Instrukcje widoczne: {len(filtered)} / {len(self._all_cards)}")

    def _rebuild_screen_pack_filter(self) -> None:
        packs = ["all"]
        for item in self._all_screen_assets:
            if item.pack not in packs:
                packs.append(item.pack)
        current = str(self.cb_screen_pack.currentData() or "all").strip().lower()
        self.cb_screen_pack.blockSignals(True)
        self.cb_screen_pack.clear()
        self.cb_screen_pack.addItem("Wszystkie pakiety", "all")
        for pack in sorted(p for p in packs if p != "all"):
            self.cb_screen_pack.addItem(pack, pack)
        idx = self.cb_screen_pack.findData(current)
        if idx >= 0:
            self.cb_screen_pack.setCurrentIndex(idx)
        self.cb_screen_pack.blockSignals(False)

    def _reload_screen_assets(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        base = project_root / "docs" / "consultation_pack"
        grouped_dirs = (
            ("Krotki pakiet", base / "screens"),
            ("QA flow", base / "screens_full" / "qa_flow_screens"),
            ("Pelne zakladki", base / "screens_full" / "qa_full_tab_screens"),
            ("Test screenshots", base / "screens_full" / "test_screenshots"),
            ("Review real", base / "screens_full" / "test_screenshots_review_real"),
        )
        assets: list[_ScreenAsset] = []
        for group, folder in grouped_dirs:
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.png")):
                assets.append(_ScreenAsset(name=path.name, pack=group, path=path))
        self._all_screen_assets = assets

    def _rebuild_screen_gallery(self) -> None:
        while self._screen_grid.count():
            item = self._screen_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_pack = str(self.cb_screen_pack.currentData() or "all").strip().lower()
        needle = str(self.ed_screen_search.text() or "").strip().lower()
        filtered: list[_ScreenAsset] = []
        for asset in self._all_screen_assets:
            if selected_pack not in ("all", "wszystkie pakiety") and asset.pack.lower() != selected_pack:
                continue
            if needle and needle not in asset.name.lower():
                continue
            filtered.append(asset)

        if not filtered:
            empty = QLabel("Brak screenow dla wybranego filtra.")
            empty.setStyleSheet("color:#64748b;font-size:12px;font-style:italic;")
            self._screen_grid.addWidget(empty, 0, 0)
        else:
            for idx, asset in enumerate(filtered):
                card = _ScreenThumbCard(asset, self._open_screen_asset, self)
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self._screen_grid.addWidget(card, idx // 3, idx % 3)

        self.lab_screen_count.setText(f"Screeny widoczne: {len(filtered)} / {len(self._all_screen_assets)}")

    def _open_visual_for_card(self, card: InstructionCardDef) -> None:
        path = str(card.visualization_path or "").strip()
        if not path:
            return
        file_path = Path(path).expanduser()
        if not file_path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))

    def _open_tab(self, title: str) -> None:
        self.sig_open_tab_requested.emit(str(title or "").strip())

    def _open_screen_asset(self, path: Path) -> None:
        if not path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_screens_index(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        index_path = project_root / "docs" / "consultation_pack" / "SCREENS_INDEX.md"
        if index_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(index_path)))

    def _build_screen_specs(self) -> tuple[_VisualLaunchSpec, ...]:
        return (
            _VisualLaunchSpec(
                title="Start",
                subtitle="centrum wejscia i decyzji",
                accent="#1f3c88",
                target_tab="Start",
                hint="Tu zaczynasz dzien, onboarding i szybkie akcje.",
            ),
            _VisualLaunchSpec(
                title="Dashboard",
                subtitle="statusy, KPI i ryzyka",
                accent="#0f172a",
                target_tab="Dashboard",
                hint="Podglad liczb i alarmow dla firmy.",
            ),
            _VisualLaunchSpec(
                title="Ekrany",
                subtitle="boty i stanowiska",
                accent="#2563eb",
                target_tab="Ekrany",
                hint="Miejsce na podglady telefonow i stanowisk pracy.",
            ),
            _VisualLaunchSpec(
                title="Kalendarz",
                subtitle="plan i statusy dni",
                accent="#7c3aed",
                target_tab="Kalendarz",
                hint="Widok terminow i postepu procesow.",
            ),
            _VisualLaunchSpec(
                title="Wycena",
                subtitle="koszty, marza i wynik",
                accent="#d97706",
                target_tab="Wycena",
                hint="Panel cen i kalkulacji do pracy handlowej.",
            ),
            _VisualLaunchSpec(
                title="Nowe zamowienie",
                subtitle="start projektu",
                accent="#059669",
                target_tab="Nowe zamowienie",
                hint="Miejsce na klienta, pracownika i dane startowe.",
            ),
        )

    def _make_panel(self) -> QFrame:
        panel = QFrame(self); panel.setProperty("uiCard", True)
        panel.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 22px;
            }
            """
        )
        return panel

    def _make_title(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setStyleSheet("color:#0f172a;font-size:15px;font-weight:900;")
        return label

    def _make_swatches(self) -> QWidget:
        holder = QWidget(self)
        layout = QGridLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        swatches = (
            ("Tlo", "#eef2f7"),
            ("Karta", "#ffffff"),
            ("Zielony", "#16a34a"),
            ("Niebieski", "#2563eb"),
            ("Fiolet", "#7c3aed"),
            ("Zolty", "#f59e0b"),
        )
        for idx, (label, color) in enumerate(swatches):
            chip = QLabel(label)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet(
                f"background:{color}; color:#ffffff; border-radius:12px; padding:8px 10px; font-size:11px; font-weight:800;"
            )
            layout.addWidget(chip, idx // 2, idx % 2)
        return holder

    def _make_status_legend(self) -> QWidget:
        holder = QWidget(self)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for text, color in (
            ("Gotowe", "#16a34a"),
            ("W toku", "#f59e0b"),
            ("Blokada", "#dc2626"),
            ("Do poprawy", "#7c3aed"),
        ):
            chip = QLabel(text)
            chip.setStyleSheet(
                f"background:{color}; color:#ffffff; border-radius:999px; padding:5px 10px; font-size:11px; font-weight:800;"
            )
            layout.addWidget(chip)
        layout.addStretch(1)
        return holder
