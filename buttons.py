from gpiozero import Button
from time import monotonic as time
DIGIT1_PIN = 16
DIGIT2_PIN = 17
CONFIRM_PIN = 19
_btn_d1 = Button(DIGIT1_PIN, bounce_time=0.05)
_btn_d2 = Button(DIGIT2_PIN, bounce_time=0.05)
_btn_ok = Button(CONFIRM_PIN, bounce_time=0.05)
digit1 = 0
digit2 = 0
_password = (0, 0)
_confirm_flag = False
_digit_changed = False
_last_digit_time = 0

def _on_digit1():
    global digit1, _digit_changed, _last_digit_time
    digit1 = (digit1 + 1) % 10
    _digit_changed = True
    _last_digit_time = time()

def _on_digit2():
    global digit2, _digit_changed, _last_digit_time
    digit2 = (digit2 + 1) % 10
    _digit_changed = True
    _last_digit_time = time()

def _on_confirm():
    global _confirm_flag
    _confirm_flag = True
_btn_d1.when_pressed = _on_digit1
_btn_d2.when_pressed = _on_digit2
_btn_ok.when_pressed = _on_confirm

def confirm_pressed() -> bool:
    """Consume the confirmation flag once."""
    global _confirm_flag
    if _confirm_flag:
        _confirm_flag = False
        return True
    return False

def digit_activity() -> bool:
    """Consume the digit-change flag once."""
    global _digit_changed
    if _digit_changed:
        _digit_changed = False
        return True
    return False

def recent_activity(window=2.0) -> bool:
    """Return whether a digit was changed within the last window seconds."""
    return time() - _last_digit_time < window

def save_password():
    """Save the current two digits in memory for this armed session."""
    global _password
    _password = (digit1, digit2)

def password_matches() -> bool:
    """Compare the current digits with the saved demo PIN."""
    return (digit1, digit2) == _password

def reset_digits():
    """Reset both input digits to zero."""
    global digit1, digit2, _digit_changed, _last_digit_time
    digit1 = 0
    digit2 = 0
    _digit_changed = False
    _last_digit_time = float('-inf')

def cleanup():
    """Release the three gpiozero button instances."""
    for button in (_btn_d1, _btn_d2, _btn_ok):
        button.close()
