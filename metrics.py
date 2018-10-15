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
       return(temperature, humidity)

def get_sun_elevation():
    sun = ephem.Sun()
    observer = ephem.Observer()
    observer.lat, observer.lon, observer.elevation = '42', '-88', 250
    observer.date = datetime.datetime.utcnow()
    sun.compute(observer)
    current_sun_alt = sun.alt
    return(current_sun_alt*180/math.pi)

# Outputs current elevation of the Sun (in degrees) and the ambient temperature and relative humidity
print get_sun_elevation()
print get_temp_and_humidity()
