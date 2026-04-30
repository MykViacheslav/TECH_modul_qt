"""
Unified Summary Panel: Łączy dane ze wszystkich 5 obszarów wyceny

Pokazuje:
- Materiały (quick + assembly + import_3d)
- Usługi (services)
- Transport/Montaż (assembly)
- GiB Lab metrics (rozkrój)
- Finalne sumy (brutto z marżą + VAT)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget
)

from src.domain.project_model import ProjectModel
from src.services.project_model_cross_tab_adapter import (
    merge_project_models, get_quick_quote_summary, get_services_summary,
    get_import_3d_summary, get_giblab_summary, get_assembly_summary
)


class UnifiedSummaryPanel(QWidget):
    """
    Unified summary dla wszystkich 5 obszarów wyceny.

    Akceptuje 5 modeli (lub ich generatory) i wyświetla:
    - Pricing breakdown (material, services, extras, base, sale, brutto)
    - Source metadata (gdzie pochodzi każda pozycja)
    - GiB Lab metrics (jeśli dostępne)
    - Full audit trail
    """

    def __init__(
        self,
        quick_quote_provider=None,
        service_provider=None,
        import_3d_provider=None,
        assembly_provider=None,
        giblab_provider=None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._quick_provider = quick_quote_provider
        self._service_provider = service_provider
        self._import_3d_provider = import_3d_provider
        self._assembly_provider = assembly_provider
        self._giblab_provider = giblab_provider

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # === HEADER ===
        head = QHBoxLayout()
        title = QLabel("Ujednolicone Podsumowanie Wyceny", self)
        title.setStyleSheet("font-size:18px; font-weight:800; color:#e8efff;")
        head.addWidget(title, 1)
        self.btn_refresh = QPushButton("Odśwież", self)
        head.addWidget(self.btn_refresh, 0)
        root.addLayout(head)

        # === SCOPE ===
        self.lab_scope = QLabel("", self)
        self.lab_scope.setWordWrap(True)
        self.lab_scope.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(self.lab_scope, 0, Qt.AlignmentFlag.AlignLeft)

        # === MAIN CONTENT (scrollable) ===
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        scroll.setWidget(content)

        # === PRICING BREAKDOWN ===
        pricing_frame = QFrame(self); pricing_frame.setProperty("uiCard", True)
        pricing_frame.setStyleSheet(
            "QFrame{background:transparent;border:1px solid #d7e1ef;border-radius:12px;}"
        )
        pricing_layout = QGridLayout(pricing_frame)
        pricing_layout.setContentsMargins(14, 14, 14, 14)
        pricing_layout.setHorizontalSpacing(16)
        pricing_layout.setVerticalSpacing(10)

        self._pricing_labels: dict[str, QLabel] = {}
        pricing_fields = [
            ("Materiały", "material_value"),
            ("Usługi", "services_total"),
            ("Transport/Montaż", "extras_total"),
            ("Razem netto", "base_total"),
            ("", ""),  # separator
            ("Marża", "profit_total"),
            ("Brutto (finał)", "brutto_total"),
        ]

        for idx, (label_text, key) in enumerate(pricing_fields):
            if not label_text:  # Separator
                continue

            r = idx
            lab = QLabel(label_text, pricing_frame)
            lab.setStyleSheet("color:#94a3b8; font-size:11px; font-weight:700;")
            val = QLabel("—", pricing_frame)
            val.setStyleSheet("color:#e8efff; font-size:14px; font-weight:800;")
            if "finał" in label_text or "netto" in label_text:
                val.setStyleSheet("color:#1e40af; font-size:16px; font-weight:900;")

            pricing_layout.addWidget(lab, r, 0)
            pricing_layout.addWidget(val, r, 1)
            self._pricing_labels[key] = val

        content_layout.addWidget(pricing_frame, 0)

        # === SOURCES BREAKDOWN ===
        sources_frame = QFrame(self); sources_frame.setProperty("uiCard", True)
        sources_frame.setStyleSheet(
            "QFrame{background:transparent;border:1px solid #e2e8f0;border-radius:12px;}"
        )
        sources_layout = QVBoxLayout(sources_frame)
        sources_layout.setContentsMargins(14, 14, 14, 14)
        sources_layout.setSpacing(8)

        sources_title = QLabel("Źródła danych", sources_frame)
        sources_title.setStyleSheet("font-size:12px; font-weight:700; color:#334155;")
        sources_layout.addWidget(sources_title)

        self.lab_sources = QLabel("", sources_frame)
        self.lab_sources.setWordWrap(True)
        self.lab_sources.setStyleSheet("color:#64748b; font-size:11px; line-height:150%;")
        sources_layout.addWidget(self.lab_sources)

        content_layout.addWidget(sources_frame, 0)

        # === GIBLAB METRICS (if available) ===
        self.giblab_frame = QFrame(self); self.giblab_frame.setProperty("uiCard", True)
        self.giblab_frame.setStyleSheet(
            "QFrame{background:#fef3c7;border:1px solid #fcd34d;border-radius:12px;}"
        )
        giblab_layout = QVBoxLayout(self.giblab_frame)
        giblab_layout.setContentsMargins(14, 14, 14, 14)
        giblab_layout.setSpacing(6)

        giblab_title = QLabel("Metryki GiB Lab (rozkrój)", self.giblab_frame)
        giblab_title.setStyleSheet("font-size:12px; font-weight:700; color:#92400e;")
        giblab_layout.addWidget(giblab_title)

        self.lab_giblab = QLabel("", self.giblab_frame)
        self.lab_giblab.setWordWrap(True)
        self.lab_giblab.setStyleSheet("color:#b45309; font-size:11px;")
        giblab_layout.addWidget(self.lab_giblab)

        self.giblab_frame.setVisible(False)  # Hidden by default
        content_layout.addWidget(self.giblab_frame, 0)

        # === AUDIT TRAIL ===
        audit_frame = QFrame(self); audit_frame.setProperty("uiCard", True)
        audit_frame.setStyleSheet(
            "QFrame{background:#f0fdf4;border:1px solid #dcfce7;border-radius:12px;}"
        )
        audit_layout = QVBoxLayout(audit_frame)
        audit_layout.setContentsMargins(14, 14, 14, 14)
        audit_layout.setSpacing(6)

        audit_title = QLabel("Audit Trail", audit_frame)
        audit_title.setStyleSheet("font-size:12px; font-weight:700; color:#166534;")
        audit_layout.addWidget(audit_title)

        self.lab_audit = QLabel("", audit_frame)
        self.lab_audit.setWordWrap(True)
        self.lab_audit.setStyleSheet("color:#15803d; font-size:10px; font-family:monospace;")
        audit_layout.addWidget(self.lab_audit)

        content_layout.addWidget(audit_frame, 0)
        content_layout.addStretch(1)

        # === CONNECT ===
        self.btn_refresh.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Regeneruje summary z wszystkich 5 źródeł."""
        # === POBIERZ MODELE ===
        models = []

        if self._quick_provider and callable(self._quick_provider):
            try:
                model = self._quick_provider()
                if model and isinstance(model, ProjectModel):
                    models.append(model)
            except Exception:
                pass

        if self._service_provider and callable(self._service_provider):
            try:
                model = self._service_provider()
                if model and isinstance(model, ProjectModel):
                    models.append(model)
            except Exception:
                pass

        if self._import_3d_provider and callable(self._import_3d_provider):
            try:
                model = self._import_3d_provider()
                if model and isinstance(model, ProjectModel):
                    models.append(model)
            except Exception:
                pass

        if self._assembly_provider and callable(self._assembly_provider):
            try:
                model = self._assembly_provider()
                if model and isinstance(model, ProjectModel):
                    models.append(model)
            except Exception:
                pass

        if not models:
            self._show_empty_state()
            return

        # === MERGE W JEDEN MODEL ===
        merged = merge_project_models(
            models,
            project_name="Ujednolicona wycena",
            merge_reason="unified_summary_refresh"
        )

        # === PRICING ===
        snapshot = merged.pricing_snapshot
        self._pricing_labels["material_value"].setText(f"{snapshot.material_value:.2f} zl")
        self._pricing_labels["services_total"].setText(f"{snapshot.services_total:.2f} zl")
        self._pricing_labels["extras_total"].setText(f"{snapshot.extras_total:.2f} zl")
        self._pricing_labels["base_total"].setText(f"{snapshot.base_total:.2f} zl")
        self._pricing_labels["profit_total"].setText(f"{snapshot.profit_total:.2f} zl")
        self._pricing_labels["brutto_total"].setText(f"{snapshot.brutto_total:.2f} zl")

        # === SCOPE ===
        scope_parts = []
        if merged.header.client_name:
            scope_parts.append(f"Klient: {merged.header.client_name}")
        if merged.header.order_code:
            scope_parts.append(f"Zamówienie: {merged.header.order_code}")
        scope_parts.append(f"Pozycji: {len(merged.quote_lines)}")
        scope_parts.append(f"Usług: {len(merged.services)}")

        self.lab_scope.setText(" | ".join(scope_parts) if scope_parts else "Brak danych")

        # === SOURCES ===
        sources_text_parts = []
        if len(models) > 0:
            sources_text_parts.append(f"Scalono {len(models)} źródła:")
        for model in models:
            source = model.source or model.audit.adapter_name or "unknown"
            sources_text_parts.append(f"  • {source}")

        self.lab_sources.setText("\n".join(sources_text_parts) if sources_text_parts else "Brak źródeł")

        # === GIBLAB ===
        if self._giblab_provider and callable(self._giblab_provider):
            try:
                giblab_model = self._giblab_provider()
                if giblab_model and isinstance(giblab_model, ProjectModel):
                    if giblab_model.giblab_result and giblab_model.giblab_result.result_path:
                        self.giblab_frame.setVisible(True)
                        util = giblab_model.giblab_result.difference_vs_theory.get("utilization_pct", 0.0)
                        scrap = giblab_model.giblab_result.scrap_m2
                        self.lab_giblab.setText(
                            f"Wykorzystanie: {util:.1f}% | Odpady: {scrap:.2f} m² | "
                            f"Arkusze: {giblab_model.giblab_result.real_sheets_count}"
                        )
                    else:
                        self.giblab_frame.setVisible(False)
            except Exception:
                self.giblab_frame.setVisible(False)

        # === AUDIT ===
        audit_parts = []
        if merged.audit.built_from:
            audit_parts.append(f"Źródła: {', '.join(merged.audit.built_from)}")
        if merged.audit.adapter_name:
            audit_parts.append(f"Adapter: {merged.audit.adapter_name}")
        if merged.audit.built_at:
            audit_parts.append(f"Czas: {merged.audit.built_at}")

        self.lab_audit.setText("\n".join(audit_parts) if audit_parts else "Brak auditu")

    def _show_empty_state(self) -> None:
        """Pokaż pusty stan gdy brak danych."""
        self.lab_scope.setText("Brak danych ze źródeł")
        for label in self._pricing_labels.values():
            label.setText("—")
        self.lab_sources.setText("Nie dostępne żadne źródła danych.")
        self.giblab_frame.setVisible(False)
        self.lab_audit.setText("N/A")
