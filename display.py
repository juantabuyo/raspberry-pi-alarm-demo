"""TM1637 display control with a cancellable countdown worker.

CLK is BCM21 and DIO is BCM20. A state change cancels and joins the old
worker before writing the new state, so stale countdown output cannot win.
"""
import threading

import tm1637

CLK = 21
DIO = 20
_display = tm1637.TM1637(clk=CLK, dio=DIO)
_display.brightness(3)
_lock = threading.RLock()
_countdown_stop = threading.Event()
_countdown_thread = None


def stop_countdown():
    """Cancel the active worker and wait until its writes have finished."""
    global _countdown_thread
    with _lock:
        stop_event = _countdown_stop
        worker = _countdown_thread
        stop_event.set()
    # Never hold the display lock while joining a worker which may need it.
    if worker is not None and worker is not threading.current_thread():
        worker.join()
    with _lock:
        if _countdown_thread is worker:
            _countdown_thread = None


def blank():
    stop_countdown()
    with _lock:
        _display.show('    ')


def show_number(number):
    with _lock:
        _display.number(max(0, min(int(number), 9999)))


def show_text(text):
    with _lock:
        _display.show(text)


def show_password(digit1, digit2):
    """Show the entered demo PIN; an active countdown may resume next tick."""
    show_text(f'  {digit1}{digit2}')


def show_armed():
    stop_countdown()
    show_text('----')


def start_countdown(seconds):
    """Show seconds down to one, then zero without an extra one-second delay.

    Each worker owns a distinct cancellation event. The FSM controls when to
    change state; this visual timer does not independently arm the system.
    """
    global _countdown_stop, _countdown_thread
    if not isinstance(seconds, int) or seconds < 0:
        raise ValueError('Countdown seconds must be a non-negative integer')
    stop_countdown()
    stop_event = threading.Event()

    def count():
        for remaining in range(seconds - 1, -1, -1):
            if stop_event.wait(1.0):
                return
            with _lock:
                if stop_event.is_set():
                    return
                _display.number(remaining)

    with _lock:
        _countdown_stop = stop_event
        _display.number(seconds)
        _countdown_thread = threading.Thread(target=count, daemon=True,
                                             name='display-countdown')
        _countdown_thread.start()


def cleanup():
    blank()
    _display.cleanup()
