import ephem, threading, logging, yaml, argparse
from time import sleep
from datetime import datetime
from gpiozero import Motor
from math import pi


def logger():
    logging.basicConfig(level=cfg['logging']['level'],
                        filename=cfg['logging']['filename'],
                        format=cfg['logging']['format'],
                        datefmt='%Y-%m-%d %H:%M:%S'
                        )

def locale():
    sun = ephem.Sun()
    observer = ephem.Observer()
    observer.lat = cfg['location']['latitude']
    observer.lon = cfg['location']['longitude']
    observer.elevation = cfg['location']['elevation']
    observer.pressure = 0
    observer.date = datetime.utcnow()
    return (sun, observer)

def sun_altitude():
    sun, observer = locale()
    sun.compute(observer)
    return sun.alt * 180 / pi

def sun_next():
    sun, observer = locale()
    observer.horizon = str(sun_altitude())
    if sun_altitude() > cfg['door']['open_elevation']:
        return observer.next_setting(ephem.Sun())
    if sun_altitude() < cfg['door']['close_elevation']:
        return observer.next_rising(ephem.Sun())

# Door functioning
def door(dir):
    if dir == 'open':
        logging.info('Door is opening')
        door_status = 'Opening'
        if not args.test:
            motor.forward()
    elif dir == 'close':
        logging.info('Door is closing')
        door_status = 'Closing'
        if not args.test:
            motor.backward()
    else:
        logging.error('Something fucky happened, dir value: {}'.format(dir))
        quit()
    sleep(cfg['door']['duration'])    
    
    if not args.test:
        motor.stop()
    
    if door_status == 'Opening':
        door_status = 'Opened'
        next_dir = 'Closing'
    
    if door_status == 'Closing':
        door_status = 'Closed'
        next_dir = 'Opening'

    logging.info('Next action: Door {} at {}'.format(next_dir, sun_next()))
    return door_status, next_dir

# Horrible printing of initial logging settings
def initial_log():
    logging.info("STARTUP ARGUMENTS - Initial Door Status: {}, Test: {}".format(args.state, str(args.test)))
    logging.info("LOCATION SETTINGS - Latitude: {}, Longitude: {}, Elevation: {}".format(cfg['location']['latitude'], cfg['location']['longitude'], cfg['location']['elevation']))
    logging.info("LOGGING SETTINGS - Level: {}, Filename: {}, Format: {}".format(cfg['logging']['level'], cfg['logging']['filename'], cfg['logging']['format']))
    logging.info("PI SETTINGS - Forward Pin: {}, Backward Pin: {}".format(cfg['pi']['forward_pin'], cfg['pi']['backward_pin']))
    logging.info("DOOR SETTINGS - Duration: {}, Open Elevation: {}, Close Elevation: {}".format(cfg['door']['duration'], cfg['door']['open_elevation'], cfg['door']['close_elevation']))

# Load Configuration File
with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

# Take in initial door status and test option from commandline
parser = argparse.ArgumentParser()
parser.add_argument('--state', type=str, required=True, help='Current state of the door.  Either open or close')
parser.add_argument('--test', action='store_true', 
    help="Runs in test mode without invoking the Rasperry Pi pins")
args = parser.parse_args()
if ((args.state != 'open') and (args.state != 'close')):
    print('You specified {}, not "open" or "close" - try again stupid'.format(args.state))
    quit()

# Set up the linear actuator's motor and what pins on the Pi triggers the relays needed for each direction.  forward opens the door, backward closes it.
if not args.test:
    motor = Motor(forward=cfg['pi']['forward_pin'], backward=cfg['pi']['backward_pin'])

# Sets up threading
open_door = threading.Thread(target=door,args=('open',))
close_door = threading.Thread(target=door,args=('close',))

door_status = args.state

# Log setup
logger()
initial_log()

def main():
    while True:
        try:
            if sun_altitude() > cfg['door']['open_elevation']:
                if door_status == 'close':
                    open_door.start()
            if sun_altitude() < cfg['door']['close_elevation']:
                if door_status == 'open':
                    close_door.start()
            logging.info("Door Status: {1}, Sun Elevation: {0:.2f}".format(sun_altitude(), door_status))
            sleep(cfg['logging']['frequency'])
        except Exception:
            logging.exception('Get an F in chat boys, this script was started in that narrow timeframe where the door would by default be neither open nor closed.  Door status: {}'.format(door_status))
            quit()

if __name__ == '__main__':
    main()