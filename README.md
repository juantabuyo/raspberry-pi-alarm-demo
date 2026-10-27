# Raspberry Pi alarm demo

We built an electronics coursework prototype combining three sensor inputs, a
five-state controller, a two-digit PIN, an RGB LED, a buzzer and a four-digit
display.
Telegram notifications are optional and disabled by default. The local demo
exercises the controller without requiring a Raspberry Pi.

![Seven state entries recorded from the controller with simulated GPIO and a manually advanced clock](docs/assets/simulated-state-trace.svg)

The saved trace records the arming delay, a triggered sensor, prealarm and
alarm, automatic rearming, and a correct PIN returning the controller to the
disarmed state. The SVG renderer was checked with Python 3.12.14 and,
separately, Python 3.12.2 on macOS. Both runs recorded the same states, times
and display outputs.
It uses simulated GPIO and time; physical hardware and notification delivery
have not been validated.

## Run the local demo

The simulation and tests passed with Python 3.12.2 on macOS and Python 3.12.14.
They need only the standard library. From this folder:

```bash
python main.py --simulate
python simulate.py --json demo-output/simulated-run.json
python -m unittest discover -s tests -v
```

To render a new trace separately from the saved SVG, run:

```bash
python tools/render_simulation.py --output demo-output/simulated-state-trace.svg
```

The renderer calls the existing simulator and records its state and display
outputs. It needs only the standard library and was checked with Python 3.12.14
and Python 3.12.2 on macOS.

Simulation substitutes GPIO interfaces, advances the clock explicitly and always
disables Telegram. It uses actual controller functions and a fictitious PIN of
42; it does not simulate electrical behaviour. The JSON command writes a separate
run under `demo-output/` and replaces that file if rerun. [Saved results](results/simulated_run.json) traverse
`DISARMED → EXIT_DELAY → ARMED → PREALARM → ALARM → ARMED → DISARMED`.
The trace's 85 seconds are simulated time, not measured hardware duration.

The console trace from `python main.py --simulate` includes:

```text
[FSM] -> DISARMED
[FSM] -> EXIT_DELAY
[FSM] -> ARMED
[FSM] Sensor triggered: Infrared threshold
[FSM] -> PREALARM
[FSM] -> ALARM
[FSM] -> ARMED
[FSM] -> DISARMED
```

This excerpt omits the repeated disabled-notification messages and the JSON
record. The full output reports `telegram_enabled: false` and a final state of
`DISARMED`.

## Controller

| State | LED | Buzzer | Display |
|---|---|---|---|
| Disarmed | Steady green | Silent | Blank or entered PIN |
| Exit delay | Accelerating blue flashes | Accelerating beeps | 15-second countdown |
| Armed | Off | Silent | `----` or entered PIN |
| Prealarm | Steady orange | Repeated short beeps | 10-second countdown or PIN |
| Alarm | Flashing red | Alternating 2/4 kHz siren | Blank or entered PIN |

A sensor threshold moves the armed controller into prealarm. After 10 seconds
it enters alarm, then rearms after 60 seconds. A correct PIN disarms from any
of these three states. Confirmation is checked before automatic transitions can
reset the digits. The PIN is chosen when arming and kept in memory; two visible
digits are a teaching mechanism, not strong access control.

The nominal scan interval is 0.1 seconds. GPIO calls, worker shutdown and
scheduling can extend it. LED and buzzer timing is not guaranteed to stay in
phase. In prealarm, a countdown tick can overwrite the displayed PIN.

## Source layout

- `main.py` implements the state machine, transition priorities and sensor polling.
- `buttons.py`, `display.py`, `rgb_led.py` and `buzzer.py` handle input and output;
  `infrared.py`, `microphone.py` and `ultrasonic.py` apply the sensor thresholds.
- `simulate.py` calls the controller with `hardware_doubles.py` and a manually
  advanced clock. It keeps the real controller logic.
- `tools/render_simulation.py` turns a new simulator run into an SVG trace.
- `notifications.py` provides optional Telegram HTTP requests; `tests/` uses
  controlled responses and never contacts Telegram.

The state machine and timing rules are coursework code. gpiozero and RPi.GPIO
provide hardware access, and `tm1637.py` adapts a third-party display driver.

## Raspberry Pi and Telegram

The intended platform is a Raspberry Pi 4 with an iMAT HAT. Check physical
wiring, voltages, sensor models, SPI setup and echo level shifting before use.
BCM connections, software thresholds and setup are in [the hardware guide](docs/hardware.md).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pi.txt
python main.py --hardware
```

Hardware installation and real GPIO/SPI, sensors, display and sound remain
**unverified**. Thresholds of 1.5 V IR, 1.0 V microphone deviation and 0.50 m
ultrasonic change are software settings, not measured detection performance.
Hardware mode has no simulation fallback. If starting part-way fails, the controller
releases the components it had already loaded before the error is reported; see the
hardware guide for what this does not cover.

To enable Telegram, export credentials from a private `.env` and use
`--hardware --enable-telegram`, following [the hardware guide](docs/hardware.md).
The program does not load `.env` automatically. Delivery is asynchronous, with a
five-second timeout and no guarantee of arrival; no real Telegram delivery has
been checked.

This is an educational prototype, without validated security, supervised restart
or power-loss protection.

## Tests and version notes

All 14 tests passed in both tested Python environments. They cover the state
path, PINs at transition boundaries, digit wraparound, sensor thresholds/priority,
countdown cancellation,
TM1637 encoding, shutdown and mocked HTTP success/errors. GPIO is replaced by
doubles; these checks do not establish electrical reliability.

`tests/test_partial_startup.py` adds five tests, each in a fresh interpreter with
the same doubles: release after a failed start, a failing cleanup not hiding the
start-up error or stopping the other cleanups, and cleanup before anything is
loaded. With the 14 original tests, all 19 passed on Python 3.12.2 on macOS.

Post-submission corrections removed embedded credentials, isolated countdown
cancellation and made PIN confirmation take priority over automatic state
changes. The five states, timings and sensor thresholds are retained.

## Academic context and credits

An *Electronic Systems* team project completed by two students, iMAT, ICAI,
Universidad Pontificia Comillas.
Hardware access uses gpiozero and RPi.GPIO. The
adapted TM1637 driver retains its [third-party attribution](THIRD_PARTY.md) and
[MIT notice](LICENSES/TM1637-MIT.txt).
