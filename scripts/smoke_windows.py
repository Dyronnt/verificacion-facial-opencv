"""Comprobar imports, recursos Qt y ventana del paquete en un proceso nuevo."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
executable = root / 'dist' / 'VerificacionFacial' / 'VerificacionFacial.exe'
if not executable.is_file():
    raise SystemExit('No se encontró la distribución Windows. Ejecuta build_windows.py primero.')
with tempfile.TemporaryDirectory() as folder:
    environment = dict(os.environ)
    environment['LOCALAPPDATA'] = folder
    environment['QT_QPA_PLATFORM'] = 'offscreen'
    subprocess.run([str(executable), '--smoke-test'], cwd=folder,
                   env=environment, check=True, timeout=60)
print('Arranque del .exe comprobado sin cámara y sin datos del participante.')
