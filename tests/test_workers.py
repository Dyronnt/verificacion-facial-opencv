import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from facial.core import Config, Engine, Store
from facial.workers import CameraWorker


class Detector:
    def empty(self):
        return False

    def detectMultiScale(self, *_args, **_kwargs):
        return [(0, 0, 160, 160)]


class Camera:
    def __init__(self, frame, stop_after=None):
        self.frame = frame
        self.stop_after = stop_after
        self.reads = 0
        self.worker = None
        self.released = False

    def isOpened(self):
        return True

    def set(self, *_):
        pass

    def read(self):
        self.reads += 1
        if self.stop_after and self.reads >= self.stop_after:
            self.worker.requestInterruption()
        return True, self.frame.copy()

    def release(self):
        self.released = True


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.frame = np.random.default_rng(7).integers(60, 220, (160, 160, 3), dtype=np.uint8)

    def run_worker(self, mode, stop_after=None):
        worker = CameraWorker(self.store, Config(), mode)
        camera = Camera(self.frame, stop_after)
        camera.worker = worker
        def engine(config, model=None):
            return Engine(config, detector=Detector(), model=model)
        with patch('facial.workers.cv2.VideoCapture', return_value=camera), \
             patch('facial.workers.Engine', side_effect=engine), \
             patch.object(CameraWorker, 'msleep'), \
             patch.object(worker, 'isInterruptionRequested', side_effect=lambda: bool(stop_after and camera.reads >= stop_after)), \
             patch('facial.workers.monotonic', side_effect=range(1000)):
            worker.run()
        self.assertTrue(camera.released)
        return worker

    def test_complete_registration_stores_35_images(self):
        self.run_worker('register')
        self.assertEqual(len(self.store.images()), 35)

    def test_cancelled_registration_keeps_previous_samples_and_model(self):
        self.store.replace_samples([cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)] * 35)
        self.store.train()
        before = self.store.model.read_bytes()
        self.run_worker('register', stop_after=3)
        self.assertEqual(len(self.store.images()), 35)
        self.assertEqual(self.store.model.read_bytes(), before)

    def test_verification_saves_calibration_and_events_without_frame_files(self):
        self.store.replace_samples([cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)] * 35)
        self.store.train()
        self.run_worker('verify', stop_after=10)
        self.assertEqual(len(self.store.rows('calibracion.csv')), 3)
        events = self.store.rows('eventos.csv')
        self.assertTrue(any(row['resultado'] == 'AUTORIZADO SIMULADO' for row in events))
        self.assertEqual(len(self.store.images()), 35)
        self.assertEqual(events[-1]['resultado'], 'FIN')


if __name__ == '__main__':
    unittest.main()
