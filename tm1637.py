# TM1637 driver for Raspberry Pi using RPi.GPIO
# Based on depklyon/raspberrypi-tm1637 (MIT License)
import RPi.GPIO as GPIO
import time

ADDR_AUTO  = 0x40
ADDR_FIXED = 0x44
STARTADDR  = 0xC0
BRIGHT_DARKEST = 0
BRIGHT_DEFAULT = 2
BRIGHT_HIGHEST = 7

SEGMENTS = [0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F,
            0x77,0x7C,0x39,0x5E,0x79,0x71,0x00]

class TM1637:
    def __init__(self, clk, dio, brightness=BRIGHT_DEFAULT):
        self.clk = clk
        self.dio = dio
        self._brightness = brightness
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.clk, GPIO.OUT)
        GPIO.setup(self.dio, GPIO.OUT)
        GPIO.output(self.clk, GPIO.LOW)
        GPIO.output(self.dio, GPIO.LOW)

    def _start(self):
        GPIO.output(self.clk, GPIO.HIGH)
        GPIO.output(self.dio, GPIO.HIGH)
        GPIO.output(self.dio, GPIO.LOW)
        GPIO.output(self.clk, GPIO.LOW)

    def _stop(self):
        GPIO.output(self.clk, GPIO.LOW)
        GPIO.output(self.dio, GPIO.LOW)
        GPIO.output(self.clk, GPIO.HIGH)
        GPIO.output(self.dio, GPIO.HIGH)

    def _write_byte(self, b):
        for i in range(8):
            GPIO.output(self.clk, GPIO.LOW)
            GPIO.output(self.dio, GPIO.HIGH if (b & 1) else GPIO.LOW)
            b >>= 1
            GPIO.output(self.clk, GPIO.HIGH)
        GPIO.output(self.clk, GPIO.LOW)
        GPIO.output(self.dio, GPIO.HIGH)
        GPIO.output(self.clk, GPIO.HIGH)
        GPIO.setup(self.dio, GPIO.IN)
        time.sleep(0.001)
        GPIO.setup(self.dio, GPIO.OUT)
        GPIO.output(self.clk, GPIO.LOW)

    def brightness(self, val=None):
        if val is None:
            return self._brightness
        self._brightness = max(0, min(7, int(val)))

    def write(self, segments, pos=0):
        self._start()
        self._write_byte(ADDR_AUTO)
        self._stop()
        self._start()
        self._write_byte(STARTADDR | pos)
        for s in segments:
            self._write_byte(s)
        self._stop()
        self._start()
        self._write_byte(0x88 | self._brightness)
        self._stop()

    def show(self, string, colon=False):
        segs = []
        for i, c in enumerate(string[:4]):
            c = c.lower()
            if c.isdigit():
                s = SEGMENTS[int(c)]
            elif c == ' ':
                s = 0x00
            elif c == '-':
                s = 0x40
            else:
                s = 0x00
            if colon and i == 1:
                s |= 0x80
            segs.append(s)
        while len(segs) < 4:
            segs.append(0x00)
        self.write(segs)

    def number(self, num):
        num = max(-999, min(9999, num))
        if num < 0:
            neg = True
            num = -num
        else:
            neg = False
        segs = [SEGMENTS[num // 1000],
                SEGMENTS[(num // 100) % 10],
                SEGMENTS[(num // 10) % 10],
                SEGMENTS[num % 10]]
        if neg:
            segs[0] = 0x40
        self.write(segs)

    def numbers(self, n1, n2, colon=True):
        segs = [SEGMENTS[n1 // 10], SEGMENTS[n1 % 10],
                SEGMENTS[n2 // 10], SEGMENTS[n2 % 10]]
        if colon:
            segs[1] |= 0x80
        self.write(segs)

    def cleanup(self):
        GPIO.cleanup([self.clk, self.dio])
