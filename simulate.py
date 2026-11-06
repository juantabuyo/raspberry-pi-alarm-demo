"""Run the actual controller with simulated GPIO and a manually advanced clock."""
import argparse
import json
from pathlib import Path

import main as controller
from hardware_doubles import RecordingDisplay


def run_demo(output=None):
    controller.load_components(simulated=True)
    clock = [0.0]
    controller._clock = lambda: clock[0]
    screen = RecordingDisplay()
    controller.display._display = screen
    states = []

    def record():
        states.append({'time_seconds': clock[0], 'state': controller.state.name,
                       'display': list(screen.history[-1])})

    try:
        controller.enter_state(controller.State.DISARMED)
        record()
        # Fictitious two-digit PIN for the demo.
        for _ in range(4):
            controller.buttons._btn_d1.press()
        for _ in range(2):
            controller.buttons._btn_d2.press()
        controller.buttons._btn_ok.press()
        controller.step()
        record()
        clock[0] = 15.0
        controller.step()
        record()
        controller.infrared._sensor.value = 1.6 / 3.3
        controller.step()
        record()
        clock[0] = 25.0
        controller.step()
        record()
        controller.step()  # The original flow sends the alert on its first alarm scan.
        controller.infrared._sensor.value = 0
        clock[0] = 85.0
        controller.step()
        record()
        for _ in range(4):
            controller.buttons._btn_d1.press()
        for _ in range(2):
            controller.buttons._btn_d2.press()
        controller.buttons._btn_ok.press()
        controller.step()
        record()
        result = {
            'kind': 'simulated peripherals and clock; no physical or network validation',
            'states': states,
            'armed_displays_correct': all(row['display'] == ['text', '----']
                                          for row in states if row['state'] == 'ARMED'),
            'final_state': controller.state.name,
            'telegram_enabled': controller.notifications._enabled,
        }
    finally:
        controller.cleanup()
    print(json.dumps(result, indent=2))
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    run_demo(parser.parse_args().json)
