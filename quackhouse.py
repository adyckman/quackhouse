#!/usr/bin/env python

import ephem
import math
import datetime
import sys
import Adafruit_DHT
import RPi.GPIO as GPIO
import time

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

def open_door():
    GPIO.output(relay_pins, (GPIO.HIGH, GPIO.LOW))
    time.sleep(60.00)
    GPIO.output(20, GPIO.LOW)
    GPIO.cleanup()

def close_door():
    GPIO.output(relay_pins, (GPIO.LOW, GPIO.HIGH))
    time.sleep(60.00)
    GPIO.output(26, GPIO.LOW)
    GPIO.cleanup()

# Sets up the GPIO pins for the motor relays to be used
relay_pins = [20,26]
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_pins, GPIO.OUT)
GPIO.output(relay_pins, GPIO.LOW)

# Outputs current elevation of the Sun (in degrees) and the ambient temperature and relative humidity
print get_sun_elevation()
print get_temp_and_humidity()
