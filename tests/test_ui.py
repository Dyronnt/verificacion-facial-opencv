import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from PySide6.QtWidgets import QApplication
from facial.core import Store
from facial.ui import Window
from facial.workers import CameraWorker
from facial.core import Config


app = QApplication.instance() or QApplication([])


class FakeCamera:
    def __init__(self, *_):
        self.released = False

    def isOpened(self):
        return False

    def release(self):
        self.released = True


class UiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.window = Window(Store(self.tmp.name))
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.window.close()
        app.processEvents()
        self.tmp.cleanup()

    def settle(self):
        deadline = time.monotonic() + 5
        while self.window.worker is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        self.assertIsNone(self.window.worker)

    def test_registration_requires_consent_and_all_pages_open(self):
        self.assertFalse(self.window.register_ui['start'].isEnabled())
        self.window.start_camera('register')
        self.assertIsNone(self.window.worker)
        self.window.register_ui['consent'].setChecked(True)
        self.assertTrue(self.window.register_ui['start'].isEnabled())
        for i in range(5):
            self.window.navigate(i)
            self.assertEqual(self.window.pages.currentIndex(), i)

    def test_missing_model_reports_error_and_recovers_controls(self):
        self.window.navigate(2)
        self.window.start_camera('verify')
        self.settle()
        self.assertEqual(self.window.verify_ui['status'].text(), 'ERROR')
        self.assertIn('Primero registra', self.window.banner.text())
        self.assertTrue(self.window.verify_ui['start'].isEnabled())

    def test_unavailable_camera_released_and_consent_reset(self):
        camera = FakeCamera()
        with patch('facial.workers.cv2.VideoCapture', return_value=camera):
            self.window.register_ui['consent'].setChecked(True)
            self.window.start_camera('register')
            self.settle()
        self.assertTrue(camera.released)
        self.assertIn('No se pudo abrir', self.window.banner.text())
        self.assertFalse(self.window.register_ui['consent'].isChecked())
        self.assertEqual(len(self.window.store.images()), 0)

    def test_close_waits_for_worker_then_closes(self):
        self.window.register_ui['consent'].setChecked(True)
        with patch('facial.workers.cv2.VideoCapture', return_value=FakeCamera()):
            self.window.start_camera('register')
            self.window.close()
            self.settle()
            app.processEvents()
        self.assertFalse(self.window.isVisible())


if __name__ == '__main__':
    unittest.main()
