# OPENCODE Templates

## Nowa zakładka (tab)

```python
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class TabName(QWidget):
    sig_open_other_tab_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.addWidget(QLabel("Nowa zakładka"))
```

## Dodawanie do registry

```python
# src/tabs/registry.py
from src.tabs.nazwa.tab_nazwa import TabNazwa

def build_tabs():
    return [
        # ...
        ("Nazwa zakładki", TabNazwa()),
    ]
```

## Dodawanie do nawigacji

```python
# src/app/navigation_groups.py
GROUPS: list[tuple[str, list[str]]] = [
    ("Grupa", ["Nazwa zakładki"]),
]
```

## Nowy CollapsibleBlock

```python
from src.ui.collapsible_block import CollapsibleBlock

self.grp_name = CollapsibleBlock("Tytuł bloku", self)
body.addWidget(self.grp_name)
layout = self.grp_name.content_layout()
```

## Sygnały między zakładkami

```python
# Źródło (np. tab_start.py)
sig_open_tab_requested = pyqtSignal(str)

# W MainWindow (main_window_wiring.py)
tab_start.sig_open_tab_requested.connect(lambda title: self._navigate_to_tab(title))

# Wywołanie
self.sig_open_tab_requested.emit("Nowa zakładka")
```

## Model danych (dataclass)

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MyModel:
    name: str = ""
    value: float = 0.0
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "items": self.items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MyModel":
        return cls(name=data.get("name", ""), value=float(data.get("value", 0.0)))
```

## JSON Store

```python
from src.storage.json_store import JsonStore

class MyStore(JsonStore):
    def __init__(self):
        super().__init__("my_data.json", "my_model")

# Użycie
store = MyStore()
items = store.get_all()
store.save(model)
```

## Test dla zakładki

```python
import pytest
from PyQt6.QtWidgets import QApplication
from src.tabs.nazwa.tab_nazwa import TabNazwa

@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_tab_creates(app):
    tab = TabNazwa()
    assert tab is not None
```

## Przycisk z ikoną

```python
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon

btn = QPushButton("Tekst")
btn.setIcon(QIcon(":/icons/name.png"))
btn.setIconSize(QSize(20, 20))
```

## Formularz z polami

```python
from PyQt6.QtWidgets import QFormLayout, QLineEdit, QSpinBox

form = QFormLayout()
self.ed_name = QLineEdit()
self.sp_value = QSpinBox()
self.sp_value.setRange(0, 1000)
form.addRow("Nazwa:", self.ed_name)
form.addRow("Wartość:", self.sp_value)
```

## Eksport do PDF

```python
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QFileDialog

printer = QPrinter()
doc = QPdfDocument()
# ... write to doc ...
path, _ = QFileDialog.getSaveFileName(self, "Zapisz PDF", "", "PDF (*.pdf)")
if path:
    doc.write(path)
```

## Eksport do HTML

```python
html = f"""
<html>
<body>
<h1>Tytuł</h1>
<p>Dane: {value}</p>
</body>
</html>
"""
with open("output.html", "w", encoding="utf-8") as f:
    f.write(html)
```
