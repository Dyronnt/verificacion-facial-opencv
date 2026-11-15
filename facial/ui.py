"""Interfaz Qt: cámara integrada, estados y acciones guiadas."""
import csv
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer, Slot
from PySide6.QtGui import QDesktopServices, QPixmap, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QStackedWidget, QGridLayout, QProgressBar, QComboBox,
    QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QDialog, QLineEdit, QDialogButtonBox, QScrollArea,
)
from .core import Config, Store
from .workers import CameraWorker, TrainingWorker

STYLE = '''
QWidget { background: #11171e; color: #e9eef4; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 14px; }
QMainWindow { background: #11171e; }
QFrame#sidebar { background: #151d26; border-right: 1px solid #2b3540; }
QFrame#card { background: #19232e; border: 1px solid #2c3a48; border-radius: 12px; }
QFrame#card QLabel { background: transparent; }
QLabel#brand { font-size: 22px; font-weight: 700; color: #6ce5c8; }
QLabel#title { font-size: 29px; font-weight: 700; }
QLabel#subtitle, QLabel#muted { color: #9cabbc; }
QLabel#section { font-size: 17px; font-weight: 600; }
QLabel#status { font-size: 23px; font-weight: 700; }
QLabel#camera { background: #0c1118; border: 1px solid #344353; border-radius: 12px; color: #8293a7; }
QPushButton { background: #263443; border: 1px solid #394b5d; border-radius: 8px; padding: 11px 16px; font-weight: 600; }
QPushButton:hover { background: #31465a; border-color: #5e7b95; }
QPushButton:disabled { color: #677787; background: #1b2530; border-color: #2a3541; }
QPushButton#primary { background: #1ec5a3; color: #082920; border-color: #30dfba; }
QPushButton#primary:hover { background: #55dbbc; }
QPushButton#primary:disabled { background: #23483f; color: #77988e; border-color: #36564d; }
QPushButton#danger { color: #ff9caa; background: #3a2530; border-color: #71404d; }
QPushButton#nav { text-align: left; padding: 14px 16px; border: 0; background: transparent; color: #aab7c7; }
QPushButton#nav:checked { background: #1c4644; color: #78f1d2; border-left: 3px solid #42dcba; }
QProgressBar { background: #0e151d; border: 0; border-radius: 4px; min-height: 8px; max-height: 8px; }
QProgressBar::chunk { background: #2dd4af; border-radius: 4px; }
QComboBox, QSpinBox, QLineEdit { background: #101922; border: 1px solid #3c4d5f; border-radius: 6px; padding: 8px; }
QComboBox QAbstractItemView { background: #19232e; selection-background-color: #28564f; }
QTableWidget { background: #151f29; alternate-background-color: #1a2632; border: 1px solid #304050; border-radius: 8px; gridline-color: #2a3947; }
QHeaderView::section { background: #243343; color: #c3d4e5; border: 0; padding: 10px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 20px; height: 20px; }
QScrollArea { border: 0; }
'''


def label(text, name=None, wrap=False):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text, callback, kind=None):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(callback)
    return b


def card():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)
    return frame, layout


class CameraView(QLabel):
    def __init__(self):
        super().__init__('Cámara detenida\n\nInicia una sesión para ver la imagen en vivo.')
        self.setObjectName('camera')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(360, 270)
        self._source = None

    def show_image(self, image):
        self._source = QPixmap.fromImage(image)
        self._paint()

    def _paint(self):
        if self._source is not None:
            self.setPixmap(self._source.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))

    def reset(self):
        self._source = None
        self.clear()
        self.setText('Cámara detenida\n\nInicia una sesión para ver la imagen en vivo.')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._paint()


class Window(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        self.worker = None
        self.pending_close = False
        self.active_mode = None
        self.session_message = None
        self.session_error = False
        self.setWindowTitle('Verificación facial · OpenCV')
        self.resize(1320, 880)
        self.setMinimumSize(1080, 760)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(224)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 28, 18, 24)
        side.setSpacing(12)
        side.addWidget(label('◉  Verificación\n    facial', 'brand'))
        side.addWidget(label('OpenCV · HT-04', 'muted'))
        side.addSpacing(28)
        self.nav = []
        for i, name in enumerate(['Inicio', 'Registro', 'Verificación', 'Resultados', 'Configuración']):
            b = button(name, lambda checked=False, index=i: self.navigate(index), 'nav')
            b.setCheckable(True)
            self.nav.append(b)
            side.addWidget(b)
        side.addStretch()
        side.addWidget(label('DATOS LOCALES', 'section'))
        side.addWidget(label('Las muestras y el modelo\npermanecen en este equipo.', 'muted', True))
        shell.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(30, 26, 30, 18)
        content.setSpacing(15)
        self.banner = label('Todo listo. Registra muestras y entrena el modelo para comenzar.', 'muted', True)
        self.banner.setMinimumHeight(44)
        content.addWidget(self.banner)
        self.pages = QStackedWidget()
        content.addWidget(self.pages, 1)
        content.addWidget(label('Sin detección de vida  ·  Simulación de acceso  ·  Uso académico', 'muted'))
        shell.addLayout(content, 1)
        self.home_page()
        self.camera_page('register')
        self.camera_page('verify')
        self.results_page()
        self.settings_page()
        self.navigate(0)
        self.refresh()

    def page(self, title, subtitle):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(label(title, 'title'))
        layout.addWidget(label(subtitle, 'subtitle', True))
        self.pages.addWidget(outer)
        return layout

    def home_page(self):
        layout = self.page('Tu espacio de verificación', 'Registra, entrena y verifica desde una sola aplicación.')
        info, col = card()
        col.addWidget(label('Un flujo sencillo. Control en cada paso.', 'section'))
        col.addWidget(label('1   Registra 35 muestras con consentimiento.\n\n2   Entrena el modelo LBPH.\n\n3   Verifica el rostro y consulta los resultados.', wrap=True))
        layout.addWidget(info)
        row = QHBoxLayout()
        self.count_label = label('', 'title')
        self.model_label = label('', 'section')
        for title, widget in [('Muestras disponibles', self.count_label), ('Estado del modelo', self.model_label)]:
            f, c = card()
            c.addWidget(label(title, 'muted'))
            c.addWidget(widget)
            row.addWidget(f)
        layout.addLayout(row)
        actions = QHBoxLayout()
        actions.addWidget(button('Registrar muestras', lambda: self.navigate(1), 'primary'))
        self.train_button = button('Entrenar modelo', self.train, 'primary')
        actions.addWidget(self.train_button)
        actions.addWidget(button('Ir a verificación', lambda: self.navigate(2)))
        layout.addLayout(actions)
        f, c = card()
        c.addWidget(label('Antes de empezar', 'section'))
        c.addWidget(label('Usa tu propio rostro o el de una persona que autorice expresamente la captura. '
                          'Un registro nuevo sustituye las muestras anteriores e invalida el modelo: deberás entrenarlo de nuevo. '
                          'Este sistema puede aceptar fotografías; la confirmación temporal no demuestra presencia real.', wrap=True))
        layout.addWidget(f)
        layout.addStretch()

    def camera_page(self, mode):
        register = mode == 'register'
        layout = self.page('Registro de muestras' if register else 'Verificación en vivo',
                           'Mira hacia la cámara y cambia ligeramente la posición, con buena iluminación.' if register
                           else 'Coloca un solo rostro frente a la cámara. La distancia LBPH no es un porcentaje.')
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        view = CameraView()
        left.addWidget(view, 1)
        consent = None
        if register:
            consent = QCheckBox('Autorizo la captura local y la sustitución de las muestras previas.')
            left.addWidget(consent)
        controls = QHBoxLayout()
        start = button('Iniciar registro' if register else 'Iniciar verificación', lambda: self.start_camera(mode), 'primary')
        stop = button('Detener', self.stop)
        stop.setEnabled(False)
        controls.addWidget(start, 2)
        controls.addWidget(stop, 1)
        left.addLayout(controls)
        body.addLayout(left, 3)
        right = QVBoxLayout()
        f, c = card()
        status = label('EN ESPERA', 'status', True)
        c.addWidget(status)
        reason = label('Inicia la cámara cuando estés listo.', 'muted', True)
        c.addWidget(reason)
        progress_text = label('Muestras: 0 / 35' if register else 'Confirmación: 0 / 8 cuadros')
        c.addWidget(progress_text)
        progress = QProgressBar()
        progress.setRange(0, 35 if register else 8)
        progress.setTextVisible(False)
        c.addWidget(progress)
        right.addWidget(f)
        f, c = card()
        metrics = {}
        for key, title in [('distance', 'Distancia LBPH'), ('threshold', 'Umbral'), ('brightness', 'Brillo'), ('sharpness', 'Nitidez')]:
            r = QHBoxLayout()
            r.addWidget(label(title, 'muted'))
            value = label('—')
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            r.addWidget(value)
            c.addLayout(r)
            metrics[key] = value
        right.addWidget(f)
        condition = None
        f, c = card()
        if register:
            c.addWidget(label('Captura con calidad', 'section'))
            c.addWidget(label('Se guardan 35 recortes de 160 × 160 píxeles. Solo se capturan cuadros con un rostro y calidad suficiente. '
                              'Si detienes antes de completar, se conservan las muestras previas.', wrap=True))
        else:
            c.addWidget(label('Calibración de umbrales', 'section'))
            c.addWidget(label('Indica quién participa para comparar 50, 65 y 80. Esta selección no autoriza el acceso.', 'muted', True))
            condition = QComboBox()
            condition.addItems(['Sin etiquetar / pausar', 'Persona registrada', 'Persona no registrada'])
            condition.currentIndexChanged.connect(self.change_condition)
            c.addWidget(condition)
        right.addWidget(f)
        right.addStretch()
        body.addLayout(right, 2)
        layout.addLayout(body, 1)
        data = dict(view=view, start=start, stop=stop, consent=consent, status=status, reason=reason,
                    progress=progress, progress_text=progress_text, metrics=metrics, condition=condition)
        if register:
            self.register_ui = data
            consent.toggled.connect(lambda checked: start.setEnabled(checked and self.worker is None))
            start.setEnabled(False)
        else:
            self.verify_ui = data

    def results_page(self):
        layout = self.page('Resultados y actividad', 'Eventos sin imágenes y comparación de umbrales de la última sesión.')
        actions = QHBoxLayout()
        actions.addWidget(button('Actualizar', self.refresh))
        actions.addWidget(button('Exportar eventos CSV', lambda: self.export('eventos.csv')))
        actions.addWidget(button('Exportar calibración CSV', lambda: self.export('calibracion.csv')))
        layout.addLayout(actions)
        layout.addWidget(label('Actividad reciente · hasta 200 eventos', 'section'))
        self.event_table = self.table(['Fecha y hora', 'Resultado', 'Motivo'])
        layout.addWidget(self.event_table, 3)
        layout.addWidget(label('Calibración · cuadros evaluados, no intentos independientes', 'section'))
        self.calibration_table = self.table(['Umbral', 'Acept. correctas', 'Rech. correctos', 'Falsas acept.', 'Falsos rech.'])
        layout.addWidget(self.calibration_table, 2)
        self.results_empty = label('', 'muted', True)
        layout.addWidget(self.results_empty)

    def table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().hide()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return table

    def settings_page(self):
        layout = self.page('Configuración', 'Los cambios se aplican en la siguiente sesión. Los ajustes se reinician al cerrar.')
        f, c = card()
        c.addWidget(label('Cámara y criterio de decisión', 'section'))
        row = QHBoxLayout()
        row.addWidget(label('Índice de cámara'))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 10)
        row.addWidget(self.camera_index)
        row.addSpacing(20)
        row.addWidget(label('Umbral LBPH'))
        self.threshold = QComboBox()
        self.threshold.addItems(['50', '65', '80'])
        self.threshold.setCurrentText('65')
        row.addWidget(self.threshold)
        c.addLayout(row)
        c.addWidget(label('Confirmación: 8 cuadros consecutivos · Brillo mínimo: 55 · Nitidez mínima: 60', 'muted', True))
        layout.addWidget(f)
        f, c = card()
        c.addWidget(label('Almacenamiento local', 'section'))
        path = label(str(self.store.root), 'muted', True)
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        c.addWidget(path)
        c.addWidget(button('Abrir carpeta de datos', self.open_folder))
        layout.addWidget(f)
        f, c = card()
        c.addWidget(label('Eliminar muestras y modelo', 'section'))
        c.addWidget(label('Requiere escribir ELIMINAR. Los registros CSV se conservan. Después deberás registrar y entrenar nuevamente.', wrap=True))
        self.delete_button = button('Eliminar datos biométricos', self.delete_data, 'danger')
        c.addWidget(self.delete_button)
        layout.addWidget(f)
        layout.addStretch()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)
        if index in (0, 3):
            self.refresh()

    def notify(self, text, error=False):
        self.banner.setText(text)
        self.banner.setStyleSheet('color: #ff9caa;' if error else 'color: #73e0c1;')

    def config(self):
        return Config(camera=self.camera_index.value(), threshold=int(self.threshold.currentText()))

    def busy(self, value):
        for b in self.nav:
            b.setEnabled(not value)
        self.train_button.setEnabled(not value and len(self.store.images()) >= 15)
        self.delete_button.setEnabled(not value)
        self.camera_index.setEnabled(not value)
        self.threshold.setEnabled(not value)
        for ui in (self.register_ui, self.verify_ui):
            ui['start'].setEnabled(not value and (ui['consent'] is None or ui['consent'].isChecked()))
            ui['stop'].setEnabled(value and isinstance(self.worker, CameraWorker))
        self.register_ui['consent'].setEnabled(not value)

    def start_camera(self, mode):
        if self.worker is not None:
            return
        if mode == 'register' and not self.register_ui['consent'].isChecked():
            self.notify('Debes autorizar la captura antes de comenzar.', True)
            return
        self.active_mode = mode
        self.session_message = None
        self.session_error = False
        ui = self.register_ui if mode == 'register' else self.verify_ui
        ui['view'].reset()
        ui['status'].setText('CONECTANDO')
        ui['status'].setStyleSheet('color: #e9eef4;')
        ui['reason'].setText('Abriendo cámara…')
        ui['progress'].setValue(0)
        ui['progress_text'].setText('Muestras: 0 / 35' if mode == 'register' else 'Confirmación: 0 / 8 cuadros')
        for value in ui['metrics'].values():
            value.setText('—')
        self.worker = CameraWorker(self.store, self.config(), mode, self)
        self.worker.frame_ready.connect(self.update_camera)
        self.worker.failed.connect(self.failed)
        self.worker.completed.connect(self.completed)
        self.worker.finished.connect(self.finished)
        self.change_condition()
        self.busy(True)
        self.notify('Sesión activa. Puedes detenerla en cualquier momento.')
        self.worker.start()

    def change_condition(self, *_):
        if isinstance(self.worker, CameraWorker) and self.worker.mode == 'verify':
            conditions = [None, 'registrada', 'no registrada']
            self.worker.set_condition(conditions[self.verify_ui['condition'].currentIndex()])

    @Slot(QImage, object, int)
    def update_camera(self, image, decision, count):
        if self.worker is None or self.worker.isInterruptionRequested():
            return
        ui = self.register_ui if self.active_mode == 'register' else self.verify_ui
        ui['view'].show_image(image)
        ui['status'].setText(decision.result)
        color = '#68e3ba' if decision.result in ('AUTORIZADO SIMULADO', 'LISTO PARA CAPTURAR') else '#efc56e'
        ui['status'].setStyleSheet(f'color: {color};')
        ui['reason'].setText(decision.reason)
        ui['progress'].setValue(count if self.active_mode == 'register' else decision.consecutive)
        ui['progress_text'].setText(f'Muestras: {count} / 35' if self.active_mode == 'register'
                                    else f'Confirmación: {decision.consecutive} / 8 cuadros')
        for key, widget in ui['metrics'].items():
            value = self.config().threshold if key == 'threshold' else getattr(decision, key)
            widget.setText('—' if value is None else f'{value:.1f}' if key == 'distance' else f'{value:.0f}')

    def train(self):
        if self.worker is not None:
            return
        self.active_mode = None
        self.session_message = None
        self.session_error = False
        self.worker = TrainingWorker(self.store, self)
        self.worker.completed.connect(self.completed)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished)
        self.busy(True)
        self.notify('Entrenando modelo LBPH… La ventana sigue disponible.')
        self.worker.start()

    def stop(self):
        if self.worker is not None:
            self.worker.requestInterruption()
            for ui in (self.register_ui, self.verify_ui):
                ui['stop'].setEnabled(False)
                if self.active_mode in ('verify', 'register'):
                    ui['view'].reset()
                    ui['status'].setText('DETENIENDO')
                    ui['reason'].setText('Liberando la cámara…')
            self.notify('Deteniendo la sesión…')

    @Slot(str)
    def failed(self, text):
        self.session_message = text
        self.session_error = True
        self.notify(text, True)

    @Slot(str)
    def completed(self, text):
        self.session_message = text
        self.notify(text)

    @Slot()
    def finished(self):
        old = self.worker
        self.worker = None
        if self.active_mode is not None:
            ui = self.register_ui if self.active_mode == 'register' else self.verify_ui
            ui['view'].reset()
            ui['status'].setText('ERROR' if self.session_error else 'REGISTRO COMPLETO'
                                 if self.session_message and self.active_mode == 'register' else 'SESIÓN FINALIZADA')
            ui['status'].setStyleSheet('color: #ff9caa;' if self.session_error else 'color: #9cabbc;')
            ui['reason'].setText(self.session_message or 'Cámara liberada. Puedes iniciar otra sesión.')
            if self.active_mode == 'verify':
                ui['progress'].setValue(0)
                ui['progress_text'].setText('Confirmación: 0 / 8 cuadros')
            else:
                self.register_ui['consent'].setChecked(False)
        if old:
            old.deleteLater()
        self.active_mode = None
        self.busy(False)
        self.refresh()
        self.notify(self.session_message or 'Sesión detenida. No se guardaron capturas incompletas.', self.session_error)
        if self.pending_close:
            QTimer.singleShot(0, self.close)

    def refresh(self):
        self.count_label.setText(str(len(self.store.images())))
        self.model_label.setText('Disponible' if self.store.model.is_file() else 'Pendiente de entrenamiento')
        if self.worker is None:
            self.train_button.setEnabled(len(self.store.images()) >= 15)
        try:
            events = self.store.rows('eventos.csv')
            calibration = self.store.rows('calibracion.csv')
            for table, rows, keys in [
                (self.event_table, list(reversed(events[-200:])), ['fecha_hora', 'resultado', 'motivo']),
                (self.calibration_table, calibration, ['umbral', 'aceptaciones_correctas', 'rechazos_correctos', 'falsas_aceptaciones', 'falsos_rechazos'])]:
                table.setRowCount(len(rows))
                for r, row in enumerate(rows):
                    for c, key in enumerate(keys):
                        item = QTableWidgetItem(row.get(key, ''))
                        item.setToolTip(row.get(key, ''))
                        table.setItem(r, c, item)
            self.results_empty.setText('Sin eventos todavía. Ejecuta una sesión para generar resultados.' if not events
                                       else 'La calibración se guarda al detener la verificación; los eventos se acumulan entre sesiones.')
        except (OSError, UnicodeError, csv.Error) as error:
            self.notify(f'No se pudieron leer los registros: {error}', True)

    def export(self, name):
        try:
            source = self.store.root / name
            if not source.is_file():
                raise ValueError('Todavía no existe este registro. Ejecuta una sesión primero.')
            path, _ = QFileDialog.getSaveFileName(self, 'Exportar resultados', name, 'CSV (*.csv)')
            if path:
                Path(path).write_bytes(source.read_bytes())
                self.notify('Resultados exportados.')
        except (OSError, ValueError) as error:
            self.notify(str(error), True)

    def open_folder(self):
        try:
            self.store.root.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.root))):
                self.notify(f'Abre manualmente esta ruta: {self.store.root}', True)
        except OSError as error:
            self.notify(str(error), True)

    def delete_data(self):
        if self.worker is not None:
            return
        if not self.store.images() and not self.store.model.exists():
            self.notify('No hay muestras ni modelo para eliminar.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Confirmar eliminación')
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Eliminar datos biométricos', 'section'))
        layout.addWidget(label(f'Se eliminarán {len(self.store.images())} muestras y el modelo, si existe. '
                               'Esta acción es irreversible. Escribe ELIMINAR para continuar.', wrap=True))
        text = QLineEdit()
        text.setPlaceholderText('ELIMINAR')
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        confirm = buttons.button(QDialogButtonBox.StandardButton.Ok)
        confirm.setText('Eliminar')
        confirm.setEnabled(False)
        text.textChanged.connect(lambda value: confirm.setEnabled(value == 'ELIMINAR'))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted and text.text() == 'ELIMINAR':
            try:
                self.store.delete_biometrics()
                self.store.event('DATOS ELIMINADOS', 'Muestras y modelo eliminados por el participante')
                self.notify('Muestras y modelo eliminados. Los CSV se conservaron.')
            except OSError as error:
                self.notify(f'No se completó la eliminación: {error}', True)
            self.refresh()

    def closeEvent(self, event):
        if self.worker is not None:
            self.pending_close = True
            self.stop()
            event.ignore()
        else:
            event.accept()
