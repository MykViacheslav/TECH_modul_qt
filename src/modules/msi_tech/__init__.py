"""
MSI Tech Module — moduł techniczny systemu ERP dla firmy meblarskiej.

Eksportuje główny serwis i modele domenowe.
"""
from .models import TechModule, BomLine, PartSpec
from .service import TechModuleService
from .repository import TechModuleRepository

__all__ = [
    "TechModule",
    "BomLine",
    "PartSpec",
    "TechModuleService",
    "TechModuleRepository",
]
