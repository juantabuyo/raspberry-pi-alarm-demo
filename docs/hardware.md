# Hardware and Telegram

The intended platform is a Raspberry Pi 4 with an iMAT HAT. These connections
and thresholds describe the software; they have **not been verified on a physical
circuit**. Local tests use GPIO doubles. Real GPIO/SPI, sensor behaviour, display
timing, sound and Telegram delivery remain unverified.

## Requirements and connections

The local simulation and all 14 tests passed with Python 3.12.2 on macOS and
Python 3.12.14. The isolated environments used pip 26.2.2; the simulation needs
no third-party packages. These checks do not validate Pi hardware support.
The Pi dependencies are
`gpiozero` and `RPi.GPIO`, listed separately in `../requirements-pi.txt`. Their
installation and versions have not been checked on a Pi.

All pin numbers are **BCM**, not physical header positions.

| Component | Software connection | Behaviour |
|---|---|---|
| Analogue IR | MCP3008 channel 0 | Voltage ≥ 1.5 V, with a 3.3 V reference |
| Microphone | MCP3008 channel 1 | Absolute deviation from 0.25 V ≥ 1.0 V |
| HC-SR04 | Trigger BCM15; echo BCM14 | Change ≥ 0.50 m from the arming reference; configured range 3 m |
| Digit buttons | BCM16 and BCM17 | Cycle digits 0–9; debounce 0.05 s |
| Confirm button | BCM19 | Save PIN and arm, or attempt disarming |
| RGB LED | Red BCM26, green BCM27, blue BCM25 | Common-cathode arrangement described by the source |
| Buzzer | BCM23 | `RPi.GPIO.PWM`, 50% duty cycle |
| TM1637 | Clock BCM21; data BCM20 | Brightness 3 of 7 |

Check the actual HAT, sensor models, supply/reference voltages, SPI configuration
and echo level shifting against the circuit before connecting devices. The code
does not establish the electrical design or identify the IR model and analogue
conditioning. No measured sensitivity or false-alarm rate is available.

## Run on the Pi

From the project folder, in your Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pi.txt
python main.py --hardware
```

Hardware mode has no simulation fallback. A missing package or inaccessible
device prevents hardware operation. Use BCM16/17 to enter the two-digit PIN and
BCM19 to confirm. Ctrl+C stops the loop and releases the inputs and outputs. The
same release runs if initialisation fails part-way: components already loaded are
released, those not yet loaded are skipped, and the original error is still the one
reported. Every loaded component is tried even when one cleanup fails; the first
such failure is raised after a normal stop, and when another error is already
propagating, the cleanup failure is only printed to stderr.

This cannot release what a component module had opened before its own import
failed (for example a first input created before a second one raised), because the
controller never receives that module. It is exercised only with the GPIO doubles,
not on a Pi. After any failed start, check the wiring and stop the process before
retrying.

The sensor priority is IR, microphone, then ultrasound; only the first active
threshold is recorded. Arming averages three consecutive ultrasonic readings
as a reference. They are not guaranteed independent. The microphone takes one
sample per scan, rather than measuring an audio envelope.

The controller scans nominally every 0.1 seconds. Hardware calls, scheduling
and worker shutdown can extend that interval. State changes cancel and join the
previous countdown before replacing it. A prealarm countdown tick can overwrite
the entered PIN on the display. LED and buzzer timing is not guaranteed to stay
in phase. See the [README](../README.md) for the five states and delays.

The PIN has only two visible digits and is held in memory. This is an educational
prototype, without validated access control, tamper detection, supervised restart,
guaranteed sensor timeouts or power-loss handling.

## Optional Telegram delivery

Telegram is disabled by default. The program reads process environment variables;
it does not load `.env` automatically. From the project folder:

```bash
cp .env.example .env
# Edit .env locally with your bot token and intended recipient.
set -a
. ./.env
set +a
python main.py --hardware --enable-telegram
```

The example contains invalid placeholders. Keep the completed `.env` private and
out of shared archives. Simulation rejects `--enable-telegram` and never contacts
the service.

Notifications use a daemon thread and a five-second HTTP timeout. There is no
guarantee of delivery, retries, durability or latency below two seconds. Errors
omit exception details and request URLs because these may contain credentials.
The tests exercise mocked HTTP responses; they do not demonstrate real delivery.

The display driver is an adaptation of third-party code: retain its
[attribution](../THIRD_PARTY.md) and [MIT notice](../LICENSES/TM1637-MIT.txt).
