"""Punto de entrada de la aplicación de escritorio."""
import sys
from PySide6.QtWidgets import QApplication
from facial.ui import Window


def main():
    application = QApplication(sys.argv)
    application.setStyle('Fusion')
    application.setApplicationName('VerificacionFacial')
    application.setOrganizationName('HT04')
    window = Window()
    window.show()
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
