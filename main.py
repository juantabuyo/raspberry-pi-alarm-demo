"""Five-state educational alarm controller.

The controller combines state entry actions with timers, a PIN and a remembered
sensor. It is a finite-state machine, not a pure Moore
machine whose entire output depends only on one of five state labels.
"""
import argparse
from enum import Enum, auto
import importlib
import sys
from time import monotonic, sleep


class State(Enum):
    DISARMED = auto()
    EXIT_DELAY = auto()
    ARMED = auto()
    PREALARM = auto()
    ALARM = auto()


EXIT_SECONDS = 15
PREALARM_SECONDS = 10
ALARM_SECONDS = 60
SCAN_SECONDS = 0.1

state = State.DISARMED
state_entered_at = 0.0
triggered_sensor = ''
alarm_notified = False
_clock = monotonic


def load_components(simulated=False, enable_telegram=False):
    """Load GPIO components only after explicit hardware or simulation selection."""
    global infrared, microphone, ultrasonic, rgb_led, display, buzzer, buttons, notifications
    if simulated:
        from hardware_doubles import install
        install()
    for name in ('infrared', 'microphone', 'ultrasonic', 'rgb_led', 'display',
                 'buzzer', 'buttons', 'notifications'):
        globals()[name] = importlib.import_module(name)
    notifications.configure(enabled=enable_telegram and not simulated)


def check_sensors():
    """Return the first active sensor in the configured priority order."""
    if infrared.presence_detected():
        return 'Infrared threshold'
    if microphone.noise_detected():
        return 'Microphone threshold'
    if ultrasonic.intrusion_detected():
        return 'Ultrasonic distance change'
    return ''


def enter_state(new_state):
    global state, state_entered_at, alarm_notified
    # Join the old visual timer before the next state's display is written.
    display.stop_countdown()
    state = new_state
    state_entered_at = _clock()
    print(f'[FSM] -> {state.name}')
    if state is State.DISARMED:
        rgb_led.steady_green()
        buzzer.stop()
        display.blank()
        buttons.reset_digits()
        notifications.send_state('DISARMED')
    elif state is State.EXIT_DELAY:
        buttons.save_password()
        buttons.reset_digits()
        rgb_led.accelerating_blue(total_duration=EXIT_SECONDS)
        buzzer.accelerating_beeps(total_duration=EXIT_SECONDS)
        display.start_countdown(EXIT_SECONDS)
    elif state is State.ARMED:
        rgb_led.off()
        buzzer.stop()
        display.show_armed()
        ultrasonic.calibrate()
        buttons.reset_digits()
        notifications.send_state('ARMED')
    elif state is State.PREALARM:
        rgb_led.steady_orange()
        buzzer.prealarm_beeps()
        display.start_countdown(PREALARM_SECONDS)
        buttons.reset_digits()
    elif state is State.ALARM:
        rgb_led.flashing_red(period=0.3)
        buzzer.start_siren()
        display.blank()
        alarm_notified = False
        buttons.reset_digits()


def try_disarm():
    if buttons.password_matches():
        enter_state(State.DISARMED)
        return True
    print('[FSM] Incorrect PIN')
    buzzer.short_beep()
    buttons.reset_digits()
    return False


def step(now=None):
    """Execute one scan; the demo may supply time without sleeping for 85 seconds."""
    global alarm_notified, triggered_sensor
    elapsed = (_clock() if now is None else now) - state_entered_at
    # Validate the entered digits before an automatic transition resets them.
    if state in (State.ARMED, State.PREALARM, State.ALARM):
        if buttons.confirm_pressed() and try_disarm():
            return
    if state is State.DISARMED:
        if buttons.digit_activity() or buttons.recent_activity():
            display.show_password(buttons.digit1, buttons.digit2)
        if buttons.confirm_pressed():
            buzzer.short_beep()
            enter_state(State.EXIT_DELAY)
    elif state is State.EXIT_DELAY:
        if elapsed >= EXIT_SECONDS:
            enter_state(State.ARMED)
    elif state is State.ARMED:
        sensor = check_sensors()
        if sensor:
            triggered_sensor = sensor
            print(f'[FSM] Sensor triggered: {sensor}')
            enter_state(State.PREALARM)
    elif state is State.PREALARM:
        if elapsed >= PREALARM_SECONDS:
            enter_state(State.ALARM)
    elif state is State.ALARM:
        if not alarm_notified:
            notifications.send_alert(triggered_sensor)
            alarm_notified = True
        if elapsed >= ALARM_SECONDS:
            enter_state(State.ARMED)
    else:
        enter_state(State.DISARMED)
    if state in (State.ARMED, State.PREALARM, State.ALARM):
        if buttons.digit_activity():
            display.show_password(buttons.digit1, buttons.digit2)


def cleanup():
    """Release outputs and gpiozero inputs, including after an interrupted loop.

    Components that were never loaded, because startup failed part-way, are
    skipped. A failing cleanup does not stop the others: every loaded component
    is tried, the first failure is raised afterwards and any further ones are
    reported on stderr.
    """
    failures = []
    for name in ('buzzer', 'rgb_led', 'display', 'buttons', 'infrared', 'microphone', 'ultrasonic'):
        module = globals().get(name)
        if module is None:
            continue
        try:
            module.cleanup()
        except Exception as error:
            failures.append((name, error))
    for name, error in failures[1:]:
        print(f'[FSM] Cleanup of {name} also failed: {error!r}', file=sys.stderr)
    if failures:
        raise failures[0][1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--simulate', action='store_true', help='Run a short scripted demo with GPIO doubles and no network')
    mode.add_argument('--hardware', action='store_true', help='Initialise the specified Raspberry Pi GPIO hardware')
    parser.add_argument('--enable-telegram', action='store_true', help='Allow configured Telegram requests in hardware mode only')
    args = parser.parse_args()
    if args.simulate:
        if args.enable_telegram:
            parser.error('Telegram cannot be enabled in simulation mode')
        from simulate import run_demo
        run_demo()
        return
    try:
        load_components(simulated=False, enable_telegram=args.enable_telegram)
        print('Raspberry Pi alarm demo')
        print('BCM16/17: digits 0–9; BCM19: confirm. Ctrl+C to stop.')
        enter_state(State.DISARMED)
        while True:
            step()
            sleep(SCAN_SECONDS)
    except KeyboardInterrupt:
        print('\n[FSM] Stopped by the user.')
    finally:
        failure = sys.exc_info()[1]  # a startup or loop error that is still propagating
        try:
            cleanup()
        except Exception as error:
            if failure is None:
                raise
            # Keep the original error as the main one; the cleanup failure is only reported.
            print(f'[FSM] Cleanup failed while handling {type(failure).__name__}: {error!r}', file=sys.stderr)


if __name__ == '__main__':
    main()
