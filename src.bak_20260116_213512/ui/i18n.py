from __future__ import annotations

from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale


_translators: list[QTranslator] = []


def apply_polish_i18n(app) -> None:
    """
    Ładuje tłumaczenia Qt na język polski (PL).
    To tłumaczy standardowe elementy Qt (np. okna dialogowe).
    """
    try:
        QLocale.setDefault(QLocale(QLocale.Polish, QLocale.Poland))
    except Exception:
        pass

    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)

    # Typowe pliki dla Qt6:
    # - qtbase_pl.qm (najważniejszy)
    # - qt_pl.qm (czasem)
    wanted = ["qtbase_pl", "qt_pl"]

    for name in wanted:
        tr = QTranslator()
        loaded = tr.load(name, translations_path)
        if loaded:
            app.installTranslator(tr)
            _translators.append(tr)
