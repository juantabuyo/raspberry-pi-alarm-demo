from gpiozero import MCP3008
_sensor = MCP3008(channel=0)
VREF = 3.3
IR_THRESHOLD_VOLTS = 1.5

def voltage() -> float:
    """Return the ADC reading in volts, using a 3.3 V reference."""
    return round(_sensor.value * VREF, 3)

def presence_detected() -> bool:
    """Compare the IR voltage with the selected 1.5 V laboratory threshold."""
    return voltage() >= IR_THRESHOLD_VOLTS

def cleanup():
    _sensor.close()
