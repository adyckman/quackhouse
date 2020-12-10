import datetime, time, ephem, math, threading, logging, yaml, argparse
from gpiozero import Motor

# Take in initial door status and test option from commandline
parser = argparse.ArgumentParser()
parser.add_argument('--state', type=str, required=True, help='Current state of the door.  Either Open or Closed')
parser.add_argument('--test', action='store_true', 
    help="Runs in test mode, without invoking the Rasperry Pi pins")
args = parser.parse_args()
if ((args.state != 'Open') and (args.state != 'Closed')):
    print('You specified {0}, not "Open" or "Closed" - try again stupid'.format(args.state))
    quit()
else:
    door_status = args.state

# Load Configuration File
with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

# Set up the linear actuator's motor and what pins on the Pi triggers the relays needed for each direction.  forward opens the door, backward closes it.
if not args.test:
    motor = Motor(forward=cfg['pi']['forward_pin'], backward=cfg['pi']['backward_pin'])

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
    #  Observer time and locaion settings here.
    observer.lat = cfg['location']['latitude']
    observer.lon = cfg['location']['longitude']
    observer.elevation = cfg['location']['elevation']
    #  Set the current time (in UTC) here
    observer.date = datetime.datetime.utcnow()
    # Computes the position of the Sun from the time/location specified above
    sun.compute(observer)
    # Returns the calculated altitude above horizon in degrees
    return sun.alt * 180 / math.pi

# Open ze door
def open_door():
    global door_status
    logging.info('Initializing Door Opening')
    door_status = 'Opening'
    logging.info(door_status)
    if not args.test:
        motor.forward()
    time.sleep(cfg['door']['duration'])
    if not args.test:
        motor.stop()
    door_status = 'Open'
    logging.info(door_status)

# Close the door
def close_door():
    global door_status
    logging.info('Initializing Door Closing')
    door_status = 'Closing'
    logging.info(door_status)
    if not args.test:
        motor.backward()
    time.sleep(cfg['door']['duration'])
    if not args.test:
        motor.stop()
    door_status = 'Closed'
    logging.info(door_status)

# Sets up threading
open_the_door = threading.Thread(target=open_door)
close_the_door = threading.Thread(target=close_door)

# Horrible printing of initial logging settings
logging.info("Current Time: {time}, Initial Door Status: {status}, Test: {test}".format(time=datetime.datetime.utcnow(), status=door_status, test=str(args.test)))
logging.info('LOCATION SETTINGS')
logging.info("Latitude: {lat}, Longitude: {lon}, Elevation: {elev}".format(lat=cfg['location']['latitude'], lon=cfg['location']['longitude'], elev=cfg['location']['elevation']))
logging.info('')
logging.info('LOGGING SETTINGS')
logging.info("Level: {lev}, Filename: {file}, Format: {format}".format(lev=cfg['logging']['level'], file=cfg['logging']['filename'], format=cfg['logging']['format']))
logging.info('')
logging.info('PI SETTINGS')
logging.info("Forward Pin: {fwd}, Backward Pin: {back}".format(fwd=cfg['pi']['forward_pin'], back=cfg['pi']['backward_pin']))
logging.info('')
logging.info('DOOR SETTINGS')
logging.info("Duration: {dur}, Open Elevation: {open}, Close Elevation: {close}".format(dur=cfg['door']['duration'], open=cfg['door']['open_elevation'], close=cfg['door']['close_elevation']))
logging.info('')

def main():
    while True:
        try:
            logging.info("Door is: {1}, Sun elevation is: {0:.2f}".format(sun_altitude(), door_status))
            if sun_altitude() > cfg['door']['open_elevation']:
                if door_status == 'Closed' or door_status == None:
                    open_the_door.start()
            if sun_altitude() < cfg['door']['close_elevation']:
                if door_status == 'Open' or door_status == None:
                    close_the_door.start()
            time.sleep(5)
        except Exception:
            logging.exception('Get an F in chat boys, this script was started in that narrow timeframe where the door would by default be neither open nor closed')

if __name__ == '__main__':
    main()