"""Construir la distribución portable desde Windows, sin datos biométricos."""
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    if sys.platform != 'win32':
        raise SystemExit('El .exe de Windows debe construirse en Windows. Usa el workflow de GitHub Actions o una PC Windows.')
    root = Path(__file__).resolve().parent.parent
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--windowed', '--onedir', '--name', 'VerificacionFacial',
        '--collect-data', 'cv2', str(root / 'app.py'),
    ], cwd=root, check=True)
    output = root / 'dist' / 'VerificacionFacial'
    shutil.copy2(root / 'README.md', output / 'LEEME.md')
    print(f'Distribución creada: {output}')
    print('Conserva la carpeta completa: el .exe necesita los archivos de _internal.')


if __name__ == '__main__':
    main()
