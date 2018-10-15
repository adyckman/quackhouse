#!/usr/bin/env python

import sys
import RPi.GPIO as GPIO
import time

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
