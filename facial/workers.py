"""Cámara y entrenamiento en hilos; la GUI recibe copias por señales."""
from threading import Lock
from time import monotonic
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from .core import Engine


class CameraWorker(QThread):
    frame_ready = Signal(QImage, object, int)
    failed = Signal(str)
    completed = Signal(str)

    def __init__(self, store, config, mode, parent=None):
        super().__init__(parent)
        self.store, self.config, self.mode = store, config, mode
        self._condition = None
        self._lock = Lock()

    def set_condition(self, condition):
        with self._lock:
            self._condition = condition

    def run(self):
        camera = None
        engine = None
        opened = False
        try:
            model = None
            if self.mode == 'verify':
                if not self.store.model.is_file():
                    raise ValueError('Primero registra muestras y entrena el modelo desde Inicio.')
                model = cv2.face.LBPHFaceRecognizer_create()
                model.read(str(self.store.model))
            engine = Engine(self.config, model=model)
            camera = cv2.VideoCapture(self.config.camera)
            if not camera.isOpened():
                raise RuntimeError('No se pudo abrir la cámara. Revisa permisos, índice y otras aplicaciones.')
            opened = True
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            images = []
            previous = None
            previous_condition = None
            captured_at = 0.0
            self.store.event('INICIO', 'Registro consentido' if self.mode == 'register' else 'Verificación iniciada')
            while not self.isInterruptionRequested():
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError('Se perdió la lectura de la cámara. Detén otras aplicaciones y vuelve a intentar.')
                with self._lock:
                    condition = self._condition
                if condition != previous_condition:
                    engine.consecutive = 0
                    previous_condition = condition
                d, roi = engine.analyze(frame, condition)
                if self.mode == 'register' and d.match and monotonic() - captured_at >= 0.15:
                    images.append(roi.copy())
                    captured_at = monotonic()
                if self.mode == 'verify' and (d.result, d.reason) != previous:
                    self.store.event(d.result, d.reason)
                    previous = (d.result, d.reason)
                if d.box:
                    x, y, w, h = d.box
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (90, 220, 140) if d.match else (90, 100, 240), 2)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, _ = rgb.shape
                image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
                self.frame_ready.emit(image, d, len(images))
                if self.mode == 'register' and len(images) == 35:
                    if self.isInterruptionRequested():
                        break
                    self.store.replace_samples(images)
                    self.store.event('REGISTRO COMPLETO', '35 muestras guardadas; es necesario entrenar')
                    self.completed.emit('Registro completo: 35 muestras. Ahora entrena el modelo desde Inicio.')
                    break
                self.msleep(35)
        except Exception as error:
            try:
                self.store.event('ERROR', str(error))
            except OSError:
                pass
            self.failed.emit(str(error))
        finally:
            if camera is not None:
                camera.release()
            if engine is not None and opened and self.mode == 'verify':
                try:
                    self.store.save_calibration(engine.stats)
                    self.store.event('FIN', 'Verificación detenida')
                except OSError as error:
                    self.failed.emit(f'No se pudieron guardar los resultados: {error}')


class TrainingWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store

    def run(self):
        try:
            if self.store.train(self.isInterruptionRequested):
                self.store.event('ENTRENADO', 'Modelo LBPH actualizado')
                self.completed.emit('Modelo entrenado. Ya puedes iniciar la verificación.')
        except Exception as error:
            self.failed.emit(str(error))
