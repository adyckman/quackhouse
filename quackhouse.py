import datetime, time, ephem, math, threading, logging, yaml
from gpiozero import Motor

# Load Configuration File
with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile)

# Set up the linear actuator's motor and what pins on the Pi triggers the relays needed for each direction.  forward opens the door, backward closes it.
motor = Motor(forward=cfg['pi']['forward_pin'], backward=cfg['pi']['backward_pin'])

# Instantanize the door's status
door_status = None

# Configure Logging
logging.basicConfig(level=cfg['logging']['level'],
                    filename=cfg['logging']['filename'],
                    format=cfg['logging']['format']
                    )

# This function calculates the sun's current relative position in the sky and returns the value in degrees.
def sun_altitude():
    # Instantanize the Sun as the object to reference
    sun = ephem.Sun()
    observer = ephem.Observer()
    #  Observer time and locaion settings here.  Based on Chicagoland, IL
    observer.lat = cfg['location']['latitude'] # Latitude
    observer.lon = cfg['location']['longitude'] # Longitude
    observer.elevation = cfg['location']['elevation'] # Elevation in Meters
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
    time.sleep(cfg['door']['duration'])
    motor.stop()
    door_status = 'Open'
    logging.info(door_status)

# Close the door
def close_door():
    global door_status
    door_status = 'Closing'
    logging.info(door_status)
    motor.backward()
    time.sleep(cfg['door']['duration'])
    motor.stop()
    door_status = 'Closed'
    logging.info(door_status)

# Sets up threading
open_the_door = threading.Thread(name='Open Door', target=open_door)
close_the_door = threading.Thread(name='Close Door', target=close_door)

def main():
    while True:
        try:
            logging.info("Door is: {1}, Sun elevation is: {0:.2f}".format(sun_altitude(), door_status))
            if sun_altitude() > 5:
                if door_status == 'Closed' or door_status == None:
                    open_the_door.start()
                    open_the_door.join()
            if sun_altitude() < -9.0:
                if door_status == 'Open' or door_status == None:
                    close_the_door.start()
                    close_the_door.join()
            time.sleep(5)
        except Exception:
            logging.exception('Get an F in chat boys')

if __name__ == '__main__':
    main()
