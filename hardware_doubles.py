"""Small in-memory GPIO doubles for tests and the explicitly selected simulation.

These expose only the APIs used by this project. They do not model electrical
behaviour, sensor timing, debounce quality or a real TM1637 bus.
"""
import sys
import types


class Device:
    def __init__(self, *args, **kwargs):
        self.closed = False

    def close(self):
        self.closed = True


class ADC(Device):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.value = 0.25 / 3.3 if channel == 1 else 0.0


class Distance(Device):
    def __init__(self, **kwargs):
        super().__init__()
        self.distance = 1.0


class Button(Device):
    def __init__(self, pin, bounce_time):
        super().__init__()
        self.pin = pin
        self.when_pressed = None

    def press(self):
        if self.when_pressed:
            self.when_pressed()


class PWMLED(Device):
    def __init__(self, pin):
        super().__init__()
        self.pin = pin
        self.value = 0


class PWM:
    def __init__(self, pin, frequency):
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0

    def start(self, duty_cycle):
        self.duty_cycle = duty_cycle

    def stop(self):
        self.duty_cycle = 0

    def ChangeFrequency(self, frequency):
        self.frequency = frequency


class RecordingDisplay:
    def __init__(self):
        self.history = []
        self.closed = False

    def brightness(self, value):
        self.brightness_value = value

    def show(self, text):
        self.history.append(('text', text))

    def number(self, number):
        self.history.append(('number', number))

    def cleanup(self):
        self.closed = True


def install():
    """Install doubles before importing the project's hardware-facing modules."""
    existing = sys.modules.get('gpiozero')
    if existing is not None:
        if getattr(existing, '_alarm_simulated', False):
            return
        raise RuntimeError('Start simulation in a fresh process without real GPIO modules loaded')
    gpiozero = types.ModuleType('gpiozero')
    gpiozero._alarm_simulated = True
    gpiozero.MCP3008 = ADC
    gpiozero.DistanceSensor = Distance
    gpiozero.Button = Button
    gpiozero.PWMLED = PWMLED
    gpio = types.ModuleType('RPi.GPIO')
    gpio.BCM, gpio.OUT, gpio.IN, gpio.HIGH, gpio.LOW = 'BCM', 'OUT', 'IN', 1, 0
    gpio.calls = []
    for operation in ('setmode', 'setwarnings', 'setup', 'output', 'cleanup'):
        setattr(gpio, operation, lambda *args, _operation=operation, **kwargs:
                gpio.calls.append((_operation, args, kwargs)))
    gpio.PWM = PWM
    rpi = types.ModuleType('RPi')
    rpi.GPIO = gpio
    sys.modules.update({'gpiozero': gpiozero, 'RPi': rpi, 'RPi.GPIO': gpio})
