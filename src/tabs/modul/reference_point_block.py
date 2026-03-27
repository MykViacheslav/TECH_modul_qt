from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from src.domain.module_models import module_type_to_cabinet_kind, normalize_module_type
from src.tabs.modul.module_defaults import MODULE_TYPE_PL


class ReferencePointBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_module_type = QComboBox()
        for key, label in MODULE_TYPE_PL.items():
            self.cb_module_type.addItem(label, key)

        self.cb_kind = QComboBox()
        self.cb_kind.addItem("Dolna (punkt od dolu)", "lower")
        self.cb_kind.addItem("Gorna (punkt od gory)", "upper")

        self.cb_ref = QComboBox()

        self.cb_module_type.currentIndexChanged.connect(self._on_module_type_changed)
        self.cb_kind.currentIndexChanged.connect(self._on_kind_changed)
        self.cb_ref.currentIndexChanged.connect(lambda _i: self.sig_changed.emit())

        form.addRow("Typ modulu", self.cb_module_type)
        form.addRow("Typ szafki", self.cb_kind)
        form.addRow("Punkt odniesienia", self.cb_ref)

        hint = QLabel("Punkt odniesienia bedzie uzyty w zakladce Sciana do ukladania modulow w komplet.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666; font-size:11px;")

        lay.addLayout(form)
        lay.addWidget(hint)

        self._fill_refs("lower")
        self.cb_module_type.setCurrentIndex(self.cb_module_type.findData("legacy"))
        self.cb_kind.setCurrentIndex(self.cb_kind.findData("lower"))

    def _fill_refs(self, kind: str) -> None:
        self.cb_ref.blockSignals(True)
        self.cb_ref.clear()
        if kind == "upper":
            self.cb_ref.addItem("Lewy-TYL-GORA (0,0,0)", "LBT")
            self.cb_ref.addItem("Srodek-TYL-GORA", "CBT")
            self.cb_ref.addItem("Prawy-TYL-GORA", "RBT")
        else:
            self.cb_ref.addItem("Lewy-TYL-DOL (0,0,0)", "LBB")
            self.cb_ref.addItem("Srodek-TYL-DOL", "CBB")
            self.cb_ref.addItem("Prawy-TYL-DOL", "RBB")
        self.cb_ref.blockSignals(False)

    def _sync_module_type_to_kind(self) -> bool:
        module_type = self.get_module_type()
        if module_type == "legacy":
            return False

        target_kind = module_type_to_cabinet_kind(module_type, fallback_kind=self.get_kind())
        idx = self.cb_kind.findData(target_kind)
        if idx < 0 or self.cb_kind.currentIndex() == idx:
            return False

        self.cb_kind.setCurrentIndex(idx)
        return True

    def _on_module_type_changed(self, _i: int) -> None:
        if self._sync_module_type_to_kind():
            return
        self.sig_changed.emit()

    def _on_kind_changed(self, _i: int) -> None:
        kind = self.get_kind()
        prev = self.get_ref()
        self._fill_refs(kind)

        if kind == "upper":
            mapping = {"LBB": "LBT", "CBB": "CBT", "RBB": "RBT"}
            self.set_ref(mapping.get(prev, "LBT"))
        else:
            mapping = {"LBT": "LBB", "CBT": "CBB", "RBT": "RBB"}
            self.set_ref(mapping.get(prev, "LBB"))

        module_type = self.get_module_type()
        if module_type != "legacy":
            normalized_type = "hanging" if kind == "upper" else ("corner" if module_type == "corner" else "legs")
            idx = self.cb_module_type.findData(normalized_type)
            if idx >= 0 and self.cb_module_type.currentIndex() != idx:
                self.cb_module_type.blockSignals(True)
                self.cb_module_type.setCurrentIndex(idx)
                self.cb_module_type.blockSignals(False)

        self.sig_changed.emit()

    def set_values(self, kind: str, ref: str, module_type: str | None = None) -> None:
        normalized_type = normalize_module_type(module_type if module_type is not None else "legacy")
        idx_type = self.cb_module_type.findData(normalized_type)
        self.cb_module_type.blockSignals(True)
        self.cb_module_type.setCurrentIndex(idx_type if idx_type >= 0 else 0)
        self.cb_module_type.blockSignals(False)

        if normalized_type != "legacy":
            kind_to_apply = module_type_to_cabinet_kind(normalized_type, fallback_kind=kind)
        else:
            kind_to_apply = str(kind or "").strip().lower() or "lower"

        fallback_kind = module_type_to_cabinet_kind(normalized_type, fallback_kind="lower")
        idx = self.cb_kind.findData(kind_to_apply)
        if idx < 0:
            idx = self.cb_kind.findData(fallback_kind)
        self.cb_kind.blockSignals(True)
        self.cb_kind.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_kind.blockSignals(False)

        self._fill_refs(self.get_kind())
        self.set_ref(ref)

    def get_module_type(self) -> str:
        return normalize_module_type(str(self.cb_module_type.currentData() or "legacy"))

    def set_ref(self, ref: str) -> None:
        idx = self.cb_ref.findData(ref)
        self.cb_ref.blockSignals(True)
        self.cb_ref.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_ref.blockSignals(False)

    def get_kind(self) -> str:
        return str(self.cb_kind.currentData() or "lower")

    def get_ref(self) -> str:
        return str(self.cb_ref.currentData() or ("LBB" if self.get_kind() == "lower" else "LBT"))
