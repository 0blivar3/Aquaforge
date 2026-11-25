from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QSurfaceFormat

from app.main_window import MainWindow
from app.theme import DARK_THEME


def main() -> int:
    surface_format = QSurfaceFormat()
    surface_format.setVersion(2, 1)
    surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    QSurfaceFormat.setDefaultFormat(surface_format)
    app = QApplication(sys.argv)
    app.setApplicationName("AquaForge")
    app.setOrganizationName("AquaForge")
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
