import unittest

from assistente_voz.activation import Action, Activation, State


class TestActivation(unittest.TestCase):
    def test_push_to_talk(self):
        a = Activation(tap_threshold_ms=400)
        self.assertEqual(a.on_press(), Action.START_RECORDING)
        self.assertEqual(a.state, State.RECORDING)
        # segurou 900ms -> push-to-talk
        self.assertEqual(a.on_release(900), Action.STOP_AND_TRANSCRIBE)
        self.assertEqual(a.state, State.TRANSCRIBING)
        a.on_transcription_done()
        self.assertEqual(a.state, State.IDLE)

    def test_tap_latches_toggle_then_second_tap_stops(self):
        a = Activation(tap_threshold_ms=400)
        self.assertEqual(a.on_press(), Action.START_RECORDING)
        # toque rápido -> trava toggle, continua gravando
        self.assertEqual(a.on_release(120), Action.LATCH_TOGGLE)
        self.assertEqual(a.state, State.RECORDING)
        # segundo toque: press para e transcreve
        self.assertEqual(a.on_press(), Action.STOP_AND_TRANSCRIBE)
        self.assertEqual(a.state, State.TRANSCRIBING)
        # o release desse segundo toque não faz nada
        self.assertEqual(a.on_release(100), Action.NONE)

    def test_no_action_while_transcribing(self):
        a = Activation()
        a.on_press()
        a.on_release(900)  # -> TRANSCRIBING
        self.assertEqual(a.on_press(), Action.NONE)
        self.assertEqual(a.on_release(50), Action.NONE)

    def test_threshold_boundary(self):
        a = Activation(tap_threshold_ms=400)
        a.on_press()
        self.assertEqual(a.on_release(400), Action.STOP_AND_TRANSCRIBE)  # >= limiar

    def test_toggle_button(self):
        a = Activation()
        self.assertEqual(a.toggle_button(), Action.START_RECORDING)
        self.assertEqual(a.state, State.RECORDING)
        self.assertEqual(a.toggle_button(), Action.STOP_AND_TRANSCRIBE)
        self.assertEqual(a.state, State.TRANSCRIBING)
        self.assertEqual(a.toggle_button(), Action.NONE)  # transcrevendo: ignora
        a.on_transcription_done()
        self.assertEqual(a.state, State.IDLE)


if __name__ == "__main__":
    unittest.main()
