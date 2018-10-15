#!/usr/bin/env python

import ephem
import math
import datetime
import sys
import Adafruit_DHT

def get_temp_and_humidity():
    sensor = Adafruit_DHT.AM2302
    gpio_pin = 4
    humidity, temperature = Adafruit_DHT.read_retry(sensor, gpio_pin)
    temperature = ( temperature * 1.8 ) + 32
    if humidity is not None and temperature is not None:
       return round(temperature, 1), round(humidity, 1)

def get_sun_elevation():
    sun = ephem.Sun()
    observer = ephem.Observer()
    observer.lat, observer.lon, observer.elevation = '42', '-88', 250
    observer.date = datetime.datetime.utcnow()
    sun.compute(observer)
    current_sun_alt = sun.alt
    return round(current_sun_alt*180/math.pi, 1)

# Outputs current elevation of the Sun (in degrees) and the ambient temperature and relative humidity
temp, humid = get_temp_and_humidity()
elevation = get_sun_elevation()
print('Temperature: {0:0.1f}F,  Relative Humidity: {1:0.1f}%'.format(temp, humid))
print('Current elevation of the sun: {0:0.2f} degrees'.format(elevation))
