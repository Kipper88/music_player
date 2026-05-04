import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
