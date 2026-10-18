import RPi.GPIO as GPIO
import threading
import time
BUZZER_PIN = 23
LOW_FREQUENCY = 2000
HIGH_FREQUENCY = 4000
DUTY_CYCLE = 50
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
_pwm = GPIO.PWM(BUZZER_PIN, LOW_FREQUENCY)
_active = False
_thread = None

def _stop():
    global _active
    _active = False
    if _thread and _thread.is_alive():
        _thread.join()
    try:
        _pwm.stop()
    except Exception:
        pass

def _siren_loop():
    _pwm.start(DUTY_CYCLE)
    while _active:
        _pwm.ChangeFrequency(HIGH_FREQUENCY)
        time.sleep(0.3)
        if not _active:
            break
        _pwm.ChangeFrequency(LOW_FREQUENCY)
        time.sleep(0.3)
    _pwm.stop()

def start_siren():
    global _active, _thread
    _stop()
    _active = True
    _thread = threading.Thread(target=_siren_loop, daemon=True)
    _thread.start()

def _prealarm_loop():
    while _active:
        _pwm.ChangeFrequency(LOW_FREQUENCY)
        _pwm.start(DUTY_CYCLE)
        time.sleep(0.1)
        _pwm.stop()
        time.sleep(0.9)

def prealarm_beeps():
    global _active, _thread
    _stop()
    _active = True
    _thread = threading.Thread(target=_prealarm_loop, daemon=True)
    _thread.start()

def _accelerating_loop(total_duration):
    started = time.monotonic()
    while _active:
        elapsed = time.monotonic() - started
        if elapsed >= total_duration:
            break
        progress = elapsed / total_duration
        period = 1.0 - 0.9 * progress
        t_beep = min(0.08, period * 0.15)
        silent_duration = period - t_beep
        _pwm.ChangeFrequency(LOW_FREQUENCY)
        _pwm.start(DUTY_CYCLE)
        time.sleep(t_beep)
        _pwm.stop()
        if not _active:
            break
        time.sleep(max(0.02, silent_duration))
    _pwm.stop()

def accelerating_beeps(total_duration=15):
    """Accelerate beeps using the same nominal period curve as the blue LED.

    Separate threads do not guarantee phase synchronisation.
    """
    global _active, _thread
    _stop()
    _active = True
    _thread = threading.Thread(target=_accelerating_loop, args=(total_duration,), daemon=True)
    _thread.start()

def short_beep(duration=0.08):
    if _active:
        return
    _pwm.ChangeFrequency(LOW_FREQUENCY)
    _pwm.start(DUTY_CYCLE)
    time.sleep(duration)
    _pwm.stop()

def stop():
    _stop()

def cleanup():
    _stop()
    GPIO.cleanup(BUZZER_PIN)
