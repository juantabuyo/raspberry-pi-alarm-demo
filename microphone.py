from gpiozero import MCP3008
_mic = MCP3008(channel=1)
VREF = 3.3
CENTRE_VOLTS = 0.25
NOISE_THRESHOLD_VOLTS = 1.0

def voltage() -> float:
    """Return the ADC reading in volts, using a 3.3 V reference."""
    return round(_mic.value * VREF, 3)

def noise_detected() -> bool:
    """Compare one microphone sample with the calibrated 0.25 V centre.

    This is a point-sample threshold, not an audio envelope or validated event detector.
    """
    return abs(voltage() - CENTRE_VOLTS) >= NOISE_THRESHOLD_VOLTS

def cleanup():
    _mic.close()
