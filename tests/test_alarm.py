"""Local checks with GPIO doubles; no hardware or Telegram service is contacted."""
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
import os
import threading
import unittest
from unittest.mock import patch
import urllib.error

from hardware_doubles import install, RecordingDisplay
install()
import main as controller
controller.load_components(simulated=True)
import buttons
import buzzer
import display
import infrared
import microphone
import notifications
import rgb_led
import tm1637
import ultrasonic


class DisplayTests(unittest.TestCase):
    def setUp(self):
        display.stop_countdown()
        self.screen = RecordingDisplay()
        display._display = self.screen

    def tearDown(self):
        display.stop_countdown()

    def test_armed_joins_old_countdown_and_is_last_write(self):
        display.start_countdown(15)
        old_worker = display._countdown_thread
        old_event = display._countdown_stop
        self.assertEqual(self.screen.history[0], ('number', 15))
        display.show_armed()
        self.assertTrue(old_event.is_set())
        self.assertFalse(old_worker.is_alive())
        self.assertEqual(self.screen.history[-1], ('text', '----'))
        self.assertIsNone(display._countdown_thread)

    def test_replacing_countdown_does_not_reactivate_old_worker(self):
        display.start_countdown(15)
        old_worker = display._countdown_thread
        old_event = display._countdown_stop
        display.start_countdown(10)
        self.assertTrue(old_event.is_set())
        self.assertFalse(old_worker.is_alive())
        self.assertIsNot(display._countdown_stop, old_event)
        display.blank()
        self.assertEqual(self.screen.history[-1], ('text', '    '))

    def test_zero_countdown_has_no_extra_delay_or_blank_write(self):
        display.start_countdown(0)
        worker = display._countdown_thread
        worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.screen.history, [('number', 0)])

    def test_driver_segments_with_gpio_double(self):
        driver = tm1637.TM1637(clk=21, dio=20)
        segments = []
        with patch.object(driver, 'write', side_effect=lambda values: segments.append(values)):
            driver.show('----')
            driver.number(42)
        self.assertEqual(segments[0], [0x40] * 4)
        self.assertEqual(segments[1], [tm1637.SEGMENTS[i] for i in [0, 0, 4, 2]])


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stdout(StringIO()))
        for module, names in [
            (rgb_led, ('steady_green', 'accelerating_blue', 'off', 'steady_orange', 'flashing_red')),
            (buzzer, ('stop', 'accelerating_beeps', 'prealarm_beeps', 'start_siren', 'short_beep')),
        ]:
            for name in names:
                self.stack.enter_context(patch.object(module, name))
        self.send_alert = self.stack.enter_context(patch.object(notifications, 'send_alert'))
        self.stack.enter_context(patch.object(notifications, 'send_state'))
        self.clock = [100.0]
        self.stack.enter_context(patch.object(controller, '_clock', side_effect=lambda: self.clock[0]))
        display.stop_countdown()
        display._display = RecordingDisplay()
        self.addCleanup(display.stop_countdown)
        buttons.reset_digits()
        buttons._confirm_flag = False
        infrared._sensor.value = 0
        microphone._mic.value = 0.25 / 3.3
        ultrasonic._sensor.distance = 1
        ultrasonic._reference_distance = None
        controller.triggered_sensor = ''
        controller.enter_state(controller.State.DISARMED)

    def arm(self):
        # Fictitious two-digit PIN 42.
        for _ in range(4):
            buttons._btn_d1.press()
        for _ in range(2):
            buttons._btn_d2.press()
        buttons._btn_ok.press()
        controller.step()
        self.assertIs(controller.state, controller.State.EXIT_DELAY)
        self.clock[0] += 15
        controller.step()
        self.assertIs(controller.state, controller.State.ARMED)
        self.assertEqual(display._display.history[-1], ('text', '----'))

    def test_full_fsm_alarm_notification_once_and_reset(self):
        self.arm()
        infrared._sensor.value = 1.5 / 3.3
        controller.step()
        self.assertIs(controller.state, controller.State.PREALARM)
        self.clock[0] += 10
        controller.step()
        self.assertIs(controller.state, controller.State.ALARM)
        controller.step()
        controller.step()
        self.send_alert.assert_called_once_with('Infrared threshold')
        infrared._sensor.value = 0
        self.clock[0] += 60
        controller.step()
        self.assertIs(controller.state, controller.State.ARMED)

    def test_wrong_then_correct_pin_disarms_during_prealarm(self):
        self.arm()
        microphone._mic.value = 1.25 / 3.3
        controller.step()
        self.assertIs(controller.state, controller.State.PREALARM)
        buttons._btn_ok.press()  # Zero digits do not match the new fixture PIN.
        controller.step()
        self.assertIs(controller.state, controller.State.PREALARM)
        for _ in range(4):
            buttons._btn_d1.press()
        for _ in range(2):
            buttons._btn_d2.press()
        buttons._btn_ok.press()
        controller.step()
        self.assertIs(controller.state, controller.State.DISARMED)
        self.assertIsNone(display._countdown_thread)

    def test_button_digits_wrap_and_flags_are_consumed(self):
        for _ in range(12):
            buttons._btn_d1.press()
        self.assertEqual(buttons.digit1, 2)
        self.assertTrue(buttons.digit_activity())
        self.assertFalse(buttons.digit_activity())
        buttons._btn_ok.press()
        self.assertTrue(buttons.confirm_pressed())
        self.assertFalse(buttons.confirm_pressed())
        buttons._btn_d2.press()
        buttons.reset_digits()
        self.assertFalse(buttons.digit_activity())

    def test_selected_sensor_thresholds_and_priority(self):
        infrared._sensor.value = 1.499 / 3.3
        self.assertFalse(infrared.presence_detected())
        infrared._sensor.value = 1.5 / 3.3
        self.assertTrue(infrared.presence_detected())
        microphone._mic.value = 1.249 / 3.3
        self.assertFalse(microphone.noise_detected())
        microphone._mic.value = 1.25 / 3.3
        self.assertTrue(microphone.noise_detected())
        self.assertEqual(controller.check_sensors(), 'Infrared threshold')
        infrared._sensor.value = 0
        self.assertEqual(controller.check_sensors(), 'Microphone threshold')
        microphone._mic.value = 0.25 / 3.3
        ultrasonic.calibrate()
        ultrasonic._sensor.distance = 1.499
        self.assertFalse(ultrasonic.intrusion_detected())
        ultrasonic._sensor.distance = 1.5
        self.assertTrue(ultrasonic.intrusion_detected())
        self.assertEqual(controller.check_sensors(), 'Ultrasonic distance change')


class NotificationTests(unittest.TestCase):
    def tearDown(self):
        notifications.configure(False)

    def test_disabled_and_example_credentials_never_request(self):
        with patch.object(notifications.urllib.request, 'urlopen') as request, redirect_stdout(StringIO()):
            notifications.configure(False)
            self.assertIsNone(notifications.send_message('Local check'))
            with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'EXAMPLE_NOT_A_TOKEN',
                                         'TELEGRAM_CHAT_ID': 'EXAMPLE_NOT_A_CHAT_ID'}):
                notifications.configure(True)
                self.assertIsNone(notifications.send_message('Local check'))
            request.assert_not_called()

    def test_mock_request_uses_timeout_and_checks_api_response(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps({'ok': True}).encode()
        output = StringIO()
        notifications.configure(True)
        with patch.object(notifications, '_credentials', return_value=('TEST_ONLY_INVALID_TOKEN', 'TEST_ONLY_INVALID_RECIPIENT')), \
             patch.object(notifications.urllib.request, 'urlopen', return_value=Response()) as request, \
             redirect_stdout(output):
            worker = notifications.send_alert('Synthetic <sensor>')
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(request.call_args.kwargs['timeout'], 5)
            self.assertIn('accepted by the API', output.getvalue())
        self.assertNotIn('TEST_ONLY_', output.getvalue())

    def test_timeout_error_output_cannot_leak_request_details(self):
        output = StringIO()
        notifications.configure(True)
        with patch.object(notifications, '_credentials', return_value=('TEST_ONLY_INVALID_TOKEN', 'TEST_ONLY_INVALID_RECIPIENT')), \
             patch.object(notifications.urllib.request, 'urlopen', side_effect=urllib.error.URLError('TEST_ONLY_INVALID_TOKEN')), \
             redirect_stdout(output):
            worker = notifications.send_message('Local check')
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
        self.assertIn('URLError', output.getvalue())
        self.assertNotIn('TEST_ONLY_INVALID_TOKEN', output.getvalue())


class OutputTests(unittest.TestCase):
    def test_stop_joins_buzzer_and_led_workers(self):
        buzzer.start_siren()
        worker = buzzer._thread
        buzzer.stop()
        self.assertFalse(worker.is_alive())
        self.assertEqual(buzzer._pwm.duty_cycle, 0)
        rgb_led.flashing_red(period=0.01)
        worker = rgb_led._effect_thread
        rgb_led.steady_green()
        self.assertFalse(worker.is_alive())
        self.assertEqual((rgb_led.red.value, rgb_led.green.value, rgb_led.blue.value), (0, 1, 0))


if __name__ == '__main__':
    unittest.main()
