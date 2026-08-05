import math
import os
import struct
import tempfile
import unittest
from pathlib import Path

from assistente_voz.audio import Recorder
from assistente_voz.usage import Usage, format_duration

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except ImportError:
    HAS_QT = False


def _pcm(amp: int, n: int = 1600) -> bytes:
    return b"".join(struct.pack("<h", int(amp * math.sin(i * 0.3))) for i in range(n))


class TestSilenceDetection(unittest.TestCase):
    def test_limiar_separa_silencio_de_fala(self):
        from assistente_voz.app import SILENCE_PEAK

        r = Recorder()
        # nada captado: tem que ficar ABAIXO do limiar
        for amp in (0, 20, 60):
            self.assertLess(r._rms_level(_pcm(amp)), SILENCE_PEAK, f"amp={amp}")
        # fala de verdade (até um sussurro): ACIMA, com folga
        for amp in (400, 800, 2500):
            self.assertGreater(r._rms_level(_pcm(amp)), SILENCE_PEAK, f"amp={amp}")

    def test_pico_acompanha_o_maior_nivel(self):
        r = Recorder()
        r.peak_level = 0.0
        for amp in (100, 3000, 200):
            r._callback(_pcm(amp), 0, 0, 0)
        self.assertGreater(r.peak_level, 0.5)     # lembrou do trecho alto
        self.assertLess(r.level, r.peak_level)    # o atual já baixou


class TestUsage(unittest.TestCase):
    def test_conta_e_soma(self):
        u = Usage(path=None)
        u.add("groq", 12.5)
        u.add("groq", 7.5)
        u.add("openai", 60)
        self.assertEqual(u.total().count, 3)
        self.assertAlmostEqual(u.total().seconds, 80.0)
        self.assertEqual(u.per_provider()["groq"].count, 2)

    def test_sem_duracao_conta_mas_nao_soma(self):
        u = Usage(path=None)
        u.add("groq")            # arquivo: duração desconhecida
        self.assertEqual(u.total().count, 1)
        self.assertEqual(u.total().seconds, 0.0)

    def test_custo_estimado(self):
        u = Usage(path=None)
        u.add("groq", 1800)      # meia hora
        self.assertAlmostEqual(u.estimated_cost(0.10), 0.05)
        self.assertEqual(u.estimated_cost(0), 0.0)   # sem taxa, sem estimativa

    def test_persistencia(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "usage.json"
            u = Usage(path=p)
            u.add("groq", 30)
            self.assertEqual(Usage(path=p).total().count, 1)
            u.reset()
            self.assertEqual(Usage(path=p).total().count, 0)

    def test_arquivo_corrompido_nao_quebra(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "usage.json"
            p.write_text("{isso não é json", encoding="utf-8")
            self.assertEqual(Usage(path=p).total().count, 0)

    def test_formato_de_duracao(self):
        self.assertEqual(format_duration(45), "45 s")
        self.assertEqual(format_duration(600), "10 min")
        self.assertEqual(format_duration(7500), "2 h 05 min")


@unittest.skipUnless(HAS_QT, "PySide6 não instalado")
class TestSilenceStopsTheCall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_audio_mudo_nao_vai_para_a_api(self):
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        c = Controller(Config(groq_api_key="k"), History(path=None))
        c.usage.path = None
        c._recorder.start = lambda: None
        c._recorder.stop = lambda: b"x" * 100
        c._recorder.last_duration_s = 3.0
        c._recorder.peak_level = 0.01          # microfone mudo
        chamou = []
        c._worker = lambda *a: chamou.append(a)
        avisos = []
        c.overlayState.connect(lambda s, t: avisos.append((s, t)))

        c._on_start()
        c._on_release(50)
        c._on_start()

        self.assertEqual(chamou, [], "mandou áudio mudo para a API")
        self.assertIn("warning", [s for s, _ in avisos])
        self.assertEqual(c.usage.total().count, 0)


if __name__ == "__main__":
    unittest.main()
