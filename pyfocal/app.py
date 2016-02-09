"""
Pyfocal front-end GUI access point.

This script will start the GUI.
"""
import sys
from qtpy.QtWidgets import *

from .ui.viewer import Viewer
from .ui.controller import Controller


class App(object):
    def __init__(self):
        super(App, self).__init__()
        self.viewer = Viewer()
        self.controller = Controller(self.viewer)


def main():
    qapp = QApplication(sys.argv)
    # qapp.setGraphicsSystem('native')

    app = App()
    app.viewer.show()
    sys.exit(qapp.exec_())


if __name__ == '__main__':
    main()
