import sys
from PyQt6.QtWidgets import QApplication
from ui_version3 import MarkovUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MarkovUI()
    window.show()
    sys.exit(app.exec())