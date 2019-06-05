#!./bin/python
import datetime, time, ephem, math, threading, logging
from gpiozero import Motor

# Set up the linear actuator's motor and what pins on the Pi triggers the relays needed for each direction.  forward opens the door, backward closes it.
motor = Motor(forward=26, backward=20)

# Instantanize the door's status
door_status = None

# Configure Logging
logging.basicConfig(level=logging.DEBUG,filename='quackhouse.log',format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')

# This function calculates the sun's current relative position in the sky and returns the value in degrees.
def sun_altitude():
    # Instantanize the Sun as the object to reference
    sun = ephem.Sun()
    observer = ephem.Observer()
    #  Observer time and locaion settings here.  Based on Chicagoland, IL
    observer.lat = '42' # Latitude
    observer.lon = '-88' # Longitude
    observer.elevation = 245 # Elevation in Meters
    #  Set the current time (in UTC) here
    observer.date = datetime.datetime.utcnow()
    # Computes the position of the Sun from the time/location specified above
    sun.compute(observer)
    # Returns the calculated altitude above horizon in degrees
    return sun.alt * 180 / math.pi

# Open ze door
def open_door():
    global door_status
    door_status = 'Opening'
    logging.info(door_status)
    motor.forward()
    time.sleep(60)
    motor.stop()
    door_status = 'Open'
    logging.info(door_status)

# Close the door
def close_door():
    global door_status
    door_status = 'Closing'
    logging.info(door_status)
    motor.backward()
    time.sleep(60)
    motor.stop()
    door_status = 'Closed'
    logging.info(door_status)

# Sets up threading
open_the_door = threading.Thread(name='Open Door', target=open_door)
close_the_door = threading.Thread(name='Close Door', target=close_door)

def main():
    while True:
        try:
            logging.info('The door is currently: %s', door_status)
            if sun_altitude() > 10:
                if door_status == 'Closed' or door_status == None:
                    open_the_door.start()
            if sun_altitude() < -6:
                if door_status == 'Open' or door_status == None:
                    close_the_door.start()
            time.sleep(5)
        except Exception:
            Logger.exception()

if __name__ == '__main__':
    main()
