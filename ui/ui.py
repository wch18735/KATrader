import sys

from kiwoom.kiwoom import Kiwoom
from PyQt5.QtWidgets import *

class UI_class():
    def __init__(self):
        print("Executed UI Class")

        # Initializing variable or functions for executing UI
        # pass the system argument value
        self.app = QApplication(sys.argv)

        self.kiwoom = Kiwoom()

        # EventLoop exec
        self.app.exec_()

    # After Design