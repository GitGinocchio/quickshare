from PyQt5.QtWidgets import QApplication
import sys

from .ui import MainWindow, AuthDialog

app = QApplication(sys.argv)
mainwindow = MainWindow()
authdialog = AuthDialog(mainwindow)
__all__ = ['app']