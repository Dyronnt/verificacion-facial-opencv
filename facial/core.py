"""Procesamiento y almacenamiento compartidos; sin dependencias de interfaz."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import csv
import os
import sys
import tempfile

import cv2
import numpy as np

THRESHOLDS = (50, 65, 80)
STAT_KEYS = ('aceptaciones_correctas', 'rechazos_correctos',
             'falsas_aceptaciones', 'falsos_rechazos')


def data_root():
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'VerificacionFacial'
    return Path(__file__).resolve().parent.parent


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else data_root()
        self.model = self.root / 'modelo' / 'lbph.yml'
        self.samples = self.root / 'datos'

    def images(self):
        return sorted(self.samples.glob('usuario1_*.png'))

    def event(self, result, reason):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / 'eventos.csv'
        new = not path.exists() or path.stat().st_size == 0
        with path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if new:
                writer.writerow(['fecha_hora', 'resultado', 'motivo'])
            writer.writerow([datetime.now().astimezone().isoformat(timespec='seconds'), result, reason])

    def rows(self, name):
        path = self.root / name
        if not path.exists():
            return []
        with path.open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))

    def save_calibration(self, stats):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / 'calibracion.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['umbral', *STAT_KEYS])
            for threshold, row in stats.items():
                writer.writerow([threshold, *(row[k] for k in STAT_KEYS)])

    def replace_samples(self, images):
        """Conservar muestras previas si se cancela antes de completar la captura."""
        if len(images) != 35:
            raise ValueError('Se requieren 35 muestras para completar el registro.')
        self.samples.mkdir(parents=True, exist_ok=True)
        # Preparar todas las imágenes antes de sustituir el registro previo.
        with tempfile.TemporaryDirectory(dir=self.samples) as temporary:
            staged = []
            for i, image in enumerate(images):
                path = Path(temporary) / f'usuario1_{i:03}.png'
                if not cv2.imwrite(str(path), image):
                    raise OSError('No se pudo guardar una muestra.')
                staged.append(path)
            # Invalidar antes del reemplazo para nunca usar un modelo obsoleto.
            self.model.unlink(missing_ok=True)
            for old in self.images():
                old.unlink()
            for path in staged:
                path.replace(self.samples / path.name)

    def train(self, cancelled=lambda: False):
        if cancelled():
            return False
        images = []
        for path in self.images():
            if cancelled():
                return False
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None and image.shape == (160, 160):
                images.append(image)
        if len(images) < 15:
            raise ValueError('Registra al menos 15 muestras válidas de 160 × 160 píxeles.')
        model = cv2.face.LBPHFaceRecognizer_create()
        model.train(images, np.ones(len(images), dtype=np.int32))
        if cancelled():
            return False
        self.model.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.model.with_name('lbph.tmp.yml')
        try:
            model.write(str(temporary))
            if cancelled():
                return False
            temporary.replace(self.model)
        finally:
            temporary.unlink(missing_ok=True)
        return True

    def delete_biometrics(self):
        failures = []
        for path in [*self.images(), self.model]:
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                failures.append(f'{path.name}: {error}')
        if failures:
            raise OSError('\n'.join(failures))


@dataclass(frozen=True)
class Config:
    camera: int = 0
    threshold: int = 65
    frames: int = 8
    brightness: int = 55
    sharpness: int = 60


@dataclass
class Decision:
    result: str = 'DENEGADO'
    reason: str = 'Ubica un solo rostro frente a la cámara'
    consecutive: int = 0
    brightness: float | None = None
    sharpness: float | None = None
    distance: float | None = None
    box: tuple | None = None
    match: bool = False


class Engine:
    def __init__(self, config=Config(), detector=None, model=None):
        self.config = config
        self.detector = detector if detector is not None else cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if self.detector.empty():
            raise RuntimeError('No se pudo cargar el detector Haar.')
        self.model = model
        self.consecutive = 0
        self.stats = {v: dict.fromkeys(STAT_KEYS, 0) for v in THRESHOLDS}

    def analyze(self, frame, condition=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
        d = Decision()
        roi = None
        if len(faces) > 1:
            d.reason = 'Hay varios rostros: debe aparecer solo uno'
        elif len(faces) == 1:
            x, y, w, h = map(int, faces[0])
            d.box = (x, y, w, h)
            roi = cv2.resize(gray[y:y+h, x:x+w], (160, 160))
            d.brightness = float(roi.mean())
            d.sharpness = float(cv2.Laplacian(roi, cv2.CV_64F).var())
            if d.brightness < self.config.brightness:
                d.reason = 'Rostro oscuro: mejora la iluminación'
            elif d.sharpness < self.config.sharpness:
                d.reason = 'Rostro borroso: ajusta distancia y enfoque'
            elif self.model is None:
                d.result = 'LISTO PARA CAPTURAR'
                d.reason = 'Calidad adecuada para el registro'
                d.match = True
            else:
                label, d.distance = self.model.predict(roi)
                d.distance = float(d.distance)
                self.calibrate(label, d.distance, condition)
                d.match = label == 1 and d.distance < self.config.threshold
                d.reason = 'El rostro no coincide con el usuario registrado'
        if self.model is not None and d.match:
            self.consecutive = min(self.consecutive + 1, self.config.frames)
            if self.consecutive == self.config.frames:
                d.result, d.reason = 'AUTORIZADO SIMULADO', 'Coincidencia confirmada'
            else:
                d.result, d.reason = 'CONFIRMANDO', 'Mantente frente a la cámara'
        else:
            self.consecutive = 0
        d.consecutive = self.consecutive
        return d, roi

    def calibrate(self, label, distance, condition):
        if condition not in ('registrada', 'no registrada'):
            return
        for threshold, stats in self.stats.items():
            accepted = label == 1 and distance < threshold
            if condition == 'registrada':
                key = 'aceptaciones_correctas' if accepted else 'falsos_rechazos'
            else:
                key = 'falsas_aceptaciones' if accepted else 'rechazos_correctos'
            stats[key] += 1
