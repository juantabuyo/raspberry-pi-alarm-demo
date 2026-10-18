from gpiozero import DistanceSensor
_sensor = DistanceSensor(echo=14, trigger=15, max_distance=3)
DISTANCE_THRESHOLD_METRES = 0.5
_reference_distance = None

def distance_cm() -> float:
    """Return the latest distance reading in centimetres."""
    return round(_sensor.distance * 100, 1)

def calibrate():
    """Average three consecutive readings as the arming reference.

    The readings are not guaranteed to be statistically independent.
    """
    global _reference_distance
    readings = []
    for _ in range(3):
        readings.append(_sensor.distance)
    _reference_distance = sum(readings) / len(readings)

def intrusion_detected() -> bool:
    """Detect an absolute distance change of at least 0.5 metres from the reference."""
    if _reference_distance is None:
        return False
    change = abs(_sensor.distance - _reference_distance)
    return change >= DISTANCE_THRESHOLD_METRES

def cleanup():
    _sensor.close()
