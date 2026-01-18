from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


class ReportProvider(Protocol):
    """
    Każda zakładka implementuje export_state() -> dict.
    To jest "rurka", którą dane spływają do pnia.
    """
    def export_state(self) -> Dict[str, Any]: ...


@dataclass
class CompanyReport:
    """
    Jeden wspólny wynik firmy (pień).
    Później dodamy tu: przychody, koszty, marże, listy, itp.
    """
    sections: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def set_section(self, key: str, data: Dict[str, Any]) -> None:
        self.sections[key] = data


def build_company_report(providers: Dict[str, ReportProvider]) -> CompanyReport:
    report = CompanyReport()
    for key, p in providers.items():
        try:
            report.set_section(key, p.export_state())
        except Exception as e:
            report.set_section(key, {"error": str(e)})
    return report
