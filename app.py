"""Punto de entrada de la aplicación de escritorio."""
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from facial.ui import Window


def main():
    application = QApplication(sys.argv)
    application.setStyle('Fusion')
    application.setApplicationName('VerificacionFacial')
    application.setOrganizationName('HT04')
    window = Window()
    window.show()
    # CI abre la ventana real sin cámara y comprueba una salida limpia.
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(500, window.close)
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
