"""Independent regression checks for a confirmation coinciding with a transition."""
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch
from hardware_doubles import install, RecordingDisplay
install()
import main as controller
controller.load_components(simulated=True)


class ConfirmationBoundaryTests(unittest.TestCase):
    def check_boundary(self, state, elapsed, saved_pin, entered_pin):
        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(StringIO()))
            for module, names in [
                (controller.rgb_led, ('steady_green', 'off', 'steady_orange', 'flashing_red')),
                (controller.buzzer, ('stop', 'prealarm_beeps', 'start_siren', 'short_beep')),
                (controller.notifications, ('send_state', 'send_alert')),
            ]:
                for name in names:
                    stack.enter_context(patch.object(module, name))
            stack.enter_context(patch.object(controller, '_clock', return_value=elapsed))
            stack.enter_context(patch.object(controller, 'check_sensors', return_value='Synthetic sensor'))
            controller.display.stop_countdown()
            controller.display._display = RecordingDisplay()
            controller.state = state
            controller.state_entered_at = 0
            controller.buttons._password = saved_pin
            controller.buttons.digit1, controller.buttons.digit2 = entered_pin
            controller.buttons._confirm_flag = True
            try:
                controller.step()
                return controller.state
            finally:
                controller.display.stop_countdown()
                controller.buttons.reset_digits()
                controller.buttons._confirm_flag = False

    def test_correct_pin_survives_sensor_and_timer_boundaries(self):
        for state, elapsed in [(controller.State.ARMED, 1),
                               (controller.State.PREALARM, 10),
                               (controller.State.ALARM, 60)]:
            with self.subTest(state=state):
                self.assertIs(self.check_boundary(state, elapsed, (4, 2), (4, 2)),
                              controller.State.DISARMED)

    def test_reset_digits_cannot_turn_wrong_pin_into_valid_zero_pin(self):
        for state, elapsed in [(controller.State.ARMED, 1),
                               (controller.State.PREALARM, 10),
                               (controller.State.ALARM, 60)]:
            with self.subTest(state=state):
                self.assertIsNot(self.check_boundary(state, elapsed, (0, 0), (9, 9)),
                                 controller.State.DISARMED)
