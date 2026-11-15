import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from facial.core import Config, Engine, Store, data_root


class Detector:
    faces = [(0, 0, 160, 160)]

    def empty(self):
        return False

    def detectMultiScale(self, *_args, **_kwargs):
        return self.faces


class Model:
    label, distance = 1, 42.0

    def predict(self, _):
        return self.label, self.distance


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.detector, self.model = Detector(), Model()
        self.engine = Engine(detector=self.detector, model=self.model)
        rng = np.random.default_rng(1)
        self.frame = rng.integers(60, 220, (160, 160, 3), dtype=np.uint8)

    def test_authorizes_only_after_eight_and_resets_on_missing_face(self):
        for _ in range(7):
            decision, _ = self.engine.analyze(self.frame)
            self.assertEqual(decision.result, 'CONFIRMANDO')
        self.assertEqual(self.engine.analyze(self.frame)[0].result, 'AUTORIZADO SIMULADO')
        self.detector.faces = []
        self.assertEqual(self.engine.analyze(self.frame)[0].consecutive, 0)
        self.detector.faces = [(0, 0, 160, 160)]
        self.assertEqual(self.engine.analyze(self.frame)[0].consecutive, 1)

    def test_multiple_faces_dark_blurry_and_nonmatch_deny(self):
        self.detector.faces = [(0, 0, 80, 80)] * 2
        self.assertEqual(self.engine.analyze(self.frame)[0].result, 'DENEGADO')
        self.detector.faces = [(0, 0, 160, 160)]
        self.assertIn('oscuro', self.engine.analyze(np.zeros_like(self.frame))[0].reason)
        self.assertIn('borroso', self.engine.analyze(np.full_like(self.frame, 120))[0].reason)
        self.model.label = 2
        self.assertEqual(self.engine.analyze(self.frame)[0].result, 'DENEGADO')

    def test_threshold_is_strict_and_calibration_needs_condition(self):
        self.engine.analyze(self.frame)
        self.assertEqual(sum(sum(row.values()) for row in self.engine.stats.values()), 0)
        self.model.distance = 65.0
        d, _ = self.engine.analyze(self.frame, 'registrada')
        self.assertFalse(d.match)
        self.assertEqual(self.engine.stats[65]['falsos_rechazos'], 1)
        self.assertEqual(self.engine.stats[80]['aceptaciones_correctas'], 1)
        self.engine.analyze(self.frame, 'no registrada')
        self.assertEqual(self.engine.stats[80]['falsas_aceptaciones'], 1)
        self.store.save_calibration(self.engine.stats)
        self.assertEqual(len(self.store.rows('calibracion.csv')), 3)

    def test_register_replaces_invalidates_model_and_trains_real_lbph(self):
        self.store.model.parent.mkdir()
        self.store.model.write_text('modelo anterior')
        images = [cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)] * 35
        self.store.replace_samples(images)
        self.assertEqual(len(self.store.images()), 35)
        self.assertFalse(self.store.model.exists())
        self.assertTrue(self.store.train())
        model = cv2.face.LBPHFaceRecognizer_create()
        model.read(str(self.store.model))
        label, distance = model.predict(images[0])
        self.assertEqual(label, 1)
        self.assertLess(distance, 1)

    def test_insufficient_invalid_images_and_cancel_do_not_publish_model(self):
        with self.assertRaises(ValueError):
            self.store.train()
        with self.assertRaises(ValueError):
            self.store.replace_samples([self.frame])
        self.assertFalse(self.store.train(lambda: True))
        self.assertFalse(self.store.model.exists())

    def test_delete_only_biometrics_preserves_csv_and_unrelated_files(self):
        self.store.samples.mkdir()
        (self.store.samples / 'usuario1_000.png').write_bytes(b'example')
        (self.store.samples / 'otra.png').write_bytes(b'example')
        self.store.event('TEST', 'sin imagen')
        self.store.delete_biometrics()
        self.assertFalse(self.store.images())
        self.assertTrue((self.store.samples / 'otra.png').exists())
        self.assertEqual(self.store.rows('eventos.csv')[0]['resultado'], 'TEST')

    def test_frozen_storage_uses_localappdata(self):
        with patch('sys.frozen', True, create=True), patch.dict('os.environ', {'LOCALAPPDATA': self.tmp.name}):
            self.assertEqual(data_root(), Path(self.tmp.name) / 'VerificacionFacial')


if __name__ == '__main__':
    unittest.main()
