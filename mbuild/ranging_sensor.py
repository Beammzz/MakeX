"""
mbuild.ranging_sensor - Laser/Ultrasonic Ranging Sensor Module
==============================================================

Distance measurement sensor for MakeX NovaPi.

Usage::

    import novapi
    from mbuild import ranging_sensor

    distance = ranging_sensor.get_distance()
    print("Distance:", distance, "cm")
"""


def get_distance(index=1):
    """Get the distance to an obstacle in front of the sensor.

    Measurement range: 2 ~ 200 cm.
    Values below 2 cm may be inaccurate.

    Args:
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        float: Distance in centimeters. Returns 0 or a very large value
            if the obstacle is out of range.
    """
    return 0.0
