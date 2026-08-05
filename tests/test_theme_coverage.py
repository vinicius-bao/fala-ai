"""Nenhum widget pode ficar com a aparência nativa do Windows.

Foi o que aconteceu com o campo de custo (QDoubleSpinBox): eu havia estilizado
QSpinBox e esqueci o irmão, e ele apareceu com a cara do sistema no meio de uma
interface própria. Este teste percorre a árvore real de widgets e cobra uma
regra no tema para cada tipo visível.
"""

import os
import re
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QWidget

    HAS_QT = True
except ImportError:
    HAS_QT = False

# Tipos que o Qt desenha do jeito do sistema se ninguém estilizar.
PRECISAM_DE_TEMA = {
    "QLineEdit",
    "QPlainTextEdit",
    "QTextEdit",
    "QComboBox",
    "QSpinBox",
    "QDoubleSpinBox",
    "QCheckBox",
    "QRadioButton",
    "QPushButton",
    "QListWidget",
    "QListView",
    "QTabBar",
    "QScrollBar",
    "QProgressBar",
    "QSlider",
    "QGroupBox",
}


# Todo widget herda destes: não contam como "tem estilo próprio".
GENERICOS = {"QWidget", "QObject", "QPaintDevice", "QFrame"}


def _qt_names(widget) -> list:
    """Nomes Qt da hierarquia (NoScrollComboBox -> QComboBox, QAbstractSpinBox…)."""
    return [
        cls.__name__
        for cls in type(widget).__mro__
        if cls.__module__.startswith("PySide6") and cls.__name__.startswith("Q")
    ]


_REGRA = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def _tipos_com_regra_base(qss: str) -> set:
    """Tipos que têm regra de aparência NORMAL (sem :foco, sem ::sub-controle).

    Só procurar o nome no QSS não serve: ele pode aparecer apenas numa regra de
    foco e o widget continuar com a cara do Windows no estado normal — foi
    exatamente o caso do campo de custo.
    """
    tipos = set()
    for seletor, _corpo in _REGRA.findall(qss):
        for parte in seletor.split(","):
            parte = parte.strip()
            if ":" in parte or not parte:
                continue          # pseudo-estado ou sub-controle: não conta
            for palavra in parte.replace("#", " ").split():
                if palavra.startswith("Q"):
                    tipos.add(palavra)
    return tipos


@unittest.skipUnless(HAS_QT, "PySide6 não instalado")
class TestThemeCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _janela(self):
        import tempfile

        os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History
        from assistente_voz.ui import MainWindow

        return MainWindow(Controller(Config(), History(path=None)))

    def _qss(self) -> str:
        from assistente_voz.theme import DARK, build_qss

        return build_qss(DARK)

    def _tipos_usados(self, raiz) -> set:
        tipos = {}
        for w in raiz.findChildren(QWidget):
            nomes = _qt_names(w)
            if nomes and nomes[0] in PRECISAM_DE_TEMA:
                tipos[nomes[0]] = type(w)
        return tipos

    def test_todo_widget_visivel_tem_aparencia_propria(self):
        from assistente_voz.onboarding import WelcomeDialog

        win = self._janela()
        dlg = WelcomeDialog(win.controller, None)
        cobertos = _tipos_com_regra_base(self._qss())
        faltando = set()
        for raiz in (win, dlg):
            for w in raiz.findChildren(QWidget):
                nomes = _qt_names(w)
                if nomes and nomes[0] in PRECISAM_DE_TEMA:
                    proprios = [n for n in nomes if n not in GENERICOS]
                    if not any(nome in cobertos for nome in proprios):
                        faltando.add(nomes[0])
        self.assertEqual(
            sorted(faltando),
            [],
            f"aparecem com o visual nativo do Windows: {sorted(faltando)}",
        )

    def test_historico_alinhado_com_a_busca(self):
        from assistente_voz.history import Transcription
        from assistente_voz.ui import HistoryCard

        win = self._janela()
        win.controller.history.add(Transcription.create("exemplo", 1.0, "groq"))
        win.refresh_history()
        win.resize(620, 700)
        win.show()
        self.app.processEvents()
        self.app.processEvents()

        def esquerda(w):
            return w.mapTo(win, w.rect().topLeft()).x()

        card = win.history_list.itemWidget(
            win.history_list.item(0)
        ).findChild(HistoryCard)
        self.assertEqual(esquerda(win.search_edit), esquerda(card))
        self.assertEqual(esquerda(win.drop_hint), esquerda(card))


if __name__ == "__main__":
    unittest.main()
