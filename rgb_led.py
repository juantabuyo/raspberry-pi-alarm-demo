from gpiozero import PWMLED
import threading
import time
RED_PIN = 26
GREEN_PIN = 27
BLUE_PIN = 25
red = PWMLED(RED_PIN)
green = PWMLED(GREEN_PIN)
blue = PWMLED(BLUE_PIN)
_effect_active = False
_effect_thread = None

def _stop_effect():
    """Stop the previous effect before applying a new LED state."""
    global _effect_active
    _effect_active = False
    if _effect_thread and _effect_thread.is_alive():
        _effect_thread.join()

def _set_colour(r, g, b):
    red.value = r
    green.value = g
    blue.value = b

def off():
    """Stop the effect and turn all LED channels off."""
    _stop_effect()
    _set_colour(0, 0, 0)

def steady_green():
    """Show steady green for the disarmed state."""
    _stop_effect()
    _set_colour(0, 1, 0)

def steady_blue():
    """Show steady blue."""
    _stop_effect()
    _set_colour(0, 0, 1)

def accelerating_blue(total_duration=15):
    """Accelerate blue flashes during the exit delay."""
    global _effect_active, _effect_thread
    _stop_effect()
    _effect_active = True

    def _accelerating_flash():
        started = time.monotonic()
        while _effect_active:
            elapsed = time.monotonic() - started
            if elapsed >= total_duration:
                _set_colour(0, 0, 1)
                break
            progress = elapsed / total_duration
            period = 1.0 - 0.9 * progress
            half_period = period / 2
            _set_colour(0, 0, 1)
            time.sleep(half_period)
            if not _effect_active:
                break
            _set_colour(0, 0, 0)
            time.sleep(half_period)
    _effect_thread = threading.Thread(target=_accelerating_flash, daemon=True)
    _effect_thread.start()

def steady_orange():
    """Show steady orange during the prealarm."""
    _stop_effect()
    _set_colour(1, 0.35, 0)

def flashing_red(period=0.5):
    """Flash red while the alarm is active."""
    global _effect_active, _effect_thread
    _stop_effect()
    _effect_active = True

    def _flash():
        while _effect_active:
            _set_colour(1, 0, 0)
            time.sleep(period)
            if not _effect_active:
                break
            _set_colour(0, 0, 0)
            time.sleep(period)
    _effect_thread = threading.Thread(target=_flash, daemon=True)
    _effect_thread.start()

def flash_error():
    """Show a short red error indication."""
    _stop_effect()
    _set_colour(1, 0, 0)
    time.sleep(0.15)
    _set_colour(0, 0, 0)
    time.sleep(0.15)
    _set_colour(1, 0, 0)
    time.sleep(0.15)
    _set_colour(0, 0, 0)

def cleanup():
    """Stop the output and release its resources."""
    _stop_effect()
    _set_colour(0, 0, 0)
    for channel in (red, green, blue):
        channel.close()
