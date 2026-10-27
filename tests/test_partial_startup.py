"""Regression tests: a failed hardware start releases the components that were already initialised.

Each case runs in a fresh interpreter. That keeps the GPIO doubles and the controller's
module state (which components are loaded) isolated from the other tests."""
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRELUDE = textwrap.dedent('''
    import importlib, sys
    sys.path.insert(0, {root!r})
    import hardware_doubles
    hardware_doubles.install()
    import main
    real_import, calls = importlib.import_module, []
    NAMES = ('buzzer', 'rgb_led', 'display', 'infrared', 'microphone', 'ultrasonic')

    def fail_import_of(component):
        def failing(name, *a, **k):
            if name == component:
                raise RuntimeError('simulated component failure')
            return real_import(name, *a, **k)
        main.importlib.import_module = failing

    def record_cleanups(failing=()):
        for name in NAMES:
            module, original = real_import(name), real_import(name).cleanup
            def wrapped(n=name, o=original):
                calls.append(n)
                if n in failing:
                    raise ValueError('cleanup failure in ' + n)
                o()
            module.cleanup = wrapped
''')


def run_isolated(body):
    script = PRELUDE.format(root=str(ROOT)) + textwrap.dedent(body)
    return subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=60)


class PartialStartup(unittest.TestCase):
    def test_initialised_components_are_released_and_the_error_is_not_hidden(self):
        result = run_isolated('''
            fail_import_of('buttons')
            record_cleanups()
            sys.argv = ['main.py', '--hardware']
            try:
                main.main()
            except RuntimeError as error:
                print('raised:', error)
            print('cleaned:', sorted(calls))
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('raised: simulated component failure', result.stdout)
        self.assertIn("cleaned: ['buzzer', 'display', 'infrared', 'microphone', 'rgb_led', 'ultrasonic']",
                      result.stdout)

    def test_cleanup_before_any_component_is_loaded_does_nothing(self):
        result = run_isolated('''
            main.cleanup()
            print('no error')
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no error', result.stdout)

    def test_one_failing_cleanup_does_not_stop_the_others(self):
        result = run_isolated('''
            main.load_components(simulated=True)
            record_cleanups(failing=('buzzer', 'display'))
            try:
                main.cleanup()
            except ValueError as error:
                print('raised:', error)
            print('cleaned:', sorted(calls))
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        # The first failure (buzzer, the first component released) is raised; the other is reported.
        self.assertIn('raised: cleanup failure in buzzer', result.stdout)
        self.assertIn("cleaned: ['buzzer', 'display', 'infrared', 'microphone', 'rgb_led', 'ultrasonic']",
                      result.stdout)
        self.assertIn('Cleanup of display also failed', result.stderr)

    def test_a_cleanup_failure_does_not_replace_the_startup_error(self):
        result = run_isolated('''
            fail_import_of('buttons')
            record_cleanups(failing=('buzzer',))
            sys.argv = ['main.py', '--hardware']
            try:
                main.main()
            except RuntimeError as error:
                print('raised:', error)
            except ValueError as error:
                print('WRONG: the cleanup error replaced the startup error:', error)
            print('cleaned:', sorted(calls))
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('raised: simulated component failure', result.stdout)
        self.assertNotIn('WRONG', result.stdout)
        # Components after the failing one were still released, and the failure was reported.
        self.assertIn("cleaned: ['buzzer', 'display', 'infrared', 'microphone', 'rgb_led', 'ultrasonic']",
                      result.stdout)
        self.assertIn('Cleanup failed while handling RuntimeError', result.stderr)

    def test_a_cleanup_failure_after_a_normal_stop_is_still_raised(self):
        result = run_isolated('''
            record_cleanups(failing=('rgb_led',))
            def interrupted(*a, **k):
                raise KeyboardInterrupt
            main.enter_state = interrupted
            sys.argv = ['main.py', '--hardware']
            try:
                main.main()
            except ValueError as error:
                print('raised:', error)
            print('cleaned:', sorted(calls))
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Stopped by the user', result.stdout)
        self.assertIn('raised: cleanup failure in rgb_led', result.stdout)
        self.assertIn("cleaned: ['buzzer', 'display', 'infrared', 'microphone', 'rgb_led', 'ultrasonic']",
                      result.stdout)


if __name__ == '__main__':
    unittest.main()
