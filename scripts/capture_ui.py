"""Capturas reproducibles de la interfaz vacía; no simulan reconocimiento."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from facial.core import Store
from facial.ui import Window

app = QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as folder:
    window = Window(Store(folder))
    window.show()
    destination = Path(__file__).resolve().parent.parent / 'docs' / 'capturas'
    destination.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(['inicio', 'registro', 'verificacion', 'resultados', 'configuracion']):
        window.navigate(index)
        app.processEvents()
        window.grab().save(str(destination / f'{name}.png'))
    window.close()
print('Capturas sin datos guardadas en docs/capturas/.')
