import ephem
import threading
import logging
import yaml
import argparse
import signal
import sys
from time import sleep
from datetime import datetime
from math import pi

try:
    from gpiozero import Motor
except ImportError:
    Motor = None


def validate_config(cfg):
    """Validate configuration, raising ValueError on any problem."""
    required = {
        'location': ['latitude', 'longitude', 'elevation'],
        'logging': ['level', 'filename', 'format', 'frequency'],
        'pi': ['forward_pin', 'backward_pin'],
        'door': ['duration', 'open_elevation', 'close_elevation'],
    }
    for section, keys in required.items():
        if section not in cfg:
            raise ValueError(f"Missing config section: '{section}'")
        for key in keys:
            if key not in cfg[section]:
                raise ValueError(f"Missing config key: '{section}.{key}'")

    try:
        float(cfg['location']['latitude'])
    except (ValueError, TypeError):
        raise ValueError(f"'location.latitude' must be a number, got: {cfg['location']['latitude']!r}")
    try:
        float(cfg['location']['longitude'])
    except (ValueError, TypeError):
        raise ValueError(f"'location.longitude' must be a number, got: {cfg['location']['longitude']!r}")

    try:
        float(cfg['location']['elevation'])
    except (ValueError, TypeError):
        raise ValueError(f"'location.elevation' must be a number, got: {cfg['location']['elevation']!r}")

    freq = cfg['logging']['frequency']
    if not isinstance(freq, (int, float)) or freq <= 0:
        raise ValueError(f"'logging.frequency' must be a positive number, got: {freq!r}")

    for pin_key in ('forward_pin', 'backward_pin'):
        val = cfg['pi'][pin_key]
        if not isinstance(val, int) or val < 0:
            raise ValueError(f"'pi.{pin_key}' must be a non-negative integer, got: {val!r}")

    dur = cfg['door']['duration']
    if not isinstance(dur, (int, float)) or dur <= 0:
        raise ValueError(f"'door.duration' must be a positive number, got: {dur!r}")

    open_el = cfg['door']['open_elevation']
    close_el = cfg['door']['close_elevation']
    if not isinstance(open_el, (int, float)):
        raise ValueError(f"'door.open_elevation' must be a number, got: {open_el!r}")
    if not isinstance(close_el, (int, float)):
        raise ValueError(f"'door.close_elevation' must be a number, got: {close_el!r}")
    if open_el <= close_el:
        raise ValueError(
            f"'door.open_elevation' ({open_el}) must be greater than 'door.close_elevation' ({close_el})"
        )


def load_config(path):
    """Load and validate a YAML config file."""
    with open(path, "r") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    validate_config(cfg)
    return cfg


def setup_logging(cfg):
    """Configure the root logger from config."""
    logging.basicConfig(
        level=cfg['logging']['level'],
        filename=cfg['logging']['filename'],
        format=cfg['logging']['format'],
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--state', type=str, required=True,
        help='Current state of the door. Either Open or Closed',
    )
    parser.add_argument(
        '--test', action='store_true',
        help="Runs in test mode without invoking the Raspberry Pi pins",
    )
    args = parser.parse_args(argv)
    if args.state not in ('Open', 'Closed'):
        parser.error(f'You specified {args.state!r}, not "Open" or "Closed" - try again')
    return args


class DoorController:
    def __init__(self, cfg, initial_state, test_mode=False):
        self._cfg = cfg
        self._test_mode = test_mode
        self._lock = threading.Lock()
        self._door_status = initial_state
        self._running = False
        self._motor = None

        if not test_mode:
            if Motor is None:
                raise RuntimeError("gpiozero is not available; use --test on non-Pi machines")
            self._motor = Motor(
                forward=cfg['pi']['forward_pin'],
                backward=cfg['pi']['backward_pin'],
            )

    @property
    def door_status(self):
        with self._lock:
            return self._door_status

    @door_status.setter
    def door_status(self, value):
        with self._lock:
            self._door_status = value

    def sun_altitude(self):
        """Calculate the sun's current altitude above the horizon in degrees."""
        # Instantiate the Sun as the object to reference
        sun = ephem.Sun()
        observer = ephem.Observer()
        # Observer time and location settings
        observer.lat = str(self._cfg['location']['latitude'])
        observer.lon = str(self._cfg['location']['longitude'])
        observer.elevation = self._cfg['location']['elevation']
        observer.pressure = 0
        # Set the time (in UTC)
        observer.date = datetime.utcnow()
        # Compute the position of the Sun
        sun.compute(observer)
        # Return the calculated altitude in degrees
        return sun.alt * 180 / pi

    def sun_next(self):
        """Calculate the time of the next sunrise or sunset relative to thresholds."""
        observer = ephem.Observer()
        # Observer time and location settings
        observer.lat = str(self._cfg['location']['latitude'])
        observer.lon = str(self._cfg['location']['longitude'])
        observer.elevation = self._cfg['location']['elevation']
        observer.pressure = 0
        observer.horizon = str(self.sun_altitude())
        if self.sun_altitude() > self._cfg['door']['open_elevation']:
            return observer.next_setting(ephem.Sun())
        if self.sun_altitude() < self._cfg['door']['close_elevation']:
            return observer.next_rising(ephem.Sun())
        return None

    def open_door(self):
        """Open the door (thread target)."""
        self.door_status = 'Opening'
        logging.info(self.door_status)
        if self._motor:
            self._motor.forward()
        sleep(self._cfg['door']['duration'])
        if self._motor:
            self._motor.stop()
        self.door_status = 'Open'
        logging.info(self.door_status)
        logging.info('Next action: Door closes at %s', self.sun_next())

    def close_door(self):
        """Close the door (thread target)."""
        self.door_status = 'Closing'
        logging.info(self.door_status)
        if self._motor:
            self._motor.backward()
        sleep(self._cfg['door']['duration'])
        if self._motor:
            self._motor.stop()
        self.door_status = 'Closed'
        logging.info(self.door_status)
        logging.info('Next action: Door opens at %s', self.sun_next())

    def log_startup(self):
        """Log initial configuration and startup state."""
        logging.info(
            "STARTUP ARGUMENTS - Initial Door Status: %s, Test: %s",
            self.door_status, self._test_mode,
        )
        logging.info(
            "LOCATION SETTINGS - Latitude: %s, Longitude: %s, Elevation: %s",
            self._cfg['location']['latitude'],
            self._cfg['location']['longitude'],
            self._cfg['location']['elevation'],
        )
        logging.info(
            "LOGGING SETTINGS - Level: %s, Filename: %s, Format: %s",
            self._cfg['logging']['level'],
            self._cfg['logging']['filename'],
            self._cfg['logging']['format'],
        )
        logging.info(
            "PI SETTINGS - Forward Pin: %s, Backward Pin: %s",
            self._cfg['pi']['forward_pin'],
            self._cfg['pi']['backward_pin'],
        )
        logging.info(
            "DOOR SETTINGS - Duration: %s, Open Elevation: %s, Close Elevation: %s",
            self._cfg['door']['duration'],
            self._cfg['door']['open_elevation'],
            self._cfg['door']['close_elevation'],
        )

    def shutdown(self):
        """Gracefully stop the controller."""
        logging.info("Shutting down")
        self._running = False
        if self._motor:
            self._motor.stop()

    def run(self):
        """Main control loop."""
        self._running = True
        while self._running:
            try:
                altitude = self.sun_altitude()
                logging.info(
                    "Door Status: %s, Sun Elevation: %.2f",
                    self.door_status, altitude,
                )
                if altitude > self._cfg['door']['open_elevation']:
                    if self.door_status in ('Closed', None):
                        t = threading.Thread(target=self.open_door)
                        t.start()
                if altitude < self._cfg['door']['close_elevation']:
                    if self.door_status in ('Open', None):
                        t = threading.Thread(target=self.close_door)
                        t.start()
                sleep(self._cfg['logging']['frequency'])
            except (KeyboardInterrupt, SystemExit):
                logging.info("Received exit signal")
                break
            except ephem.CircumpolarError:
                logging.warning("Circumpolar condition detected, retrying next cycle")
                sleep(self._cfg['logging']['frequency'])
            except OSError as e:
                logging.error("OS/GPIO error: %s", e)
                sleep(self._cfg['logging']['frequency'])
            except Exception:
                logging.exception("Unexpected error in main loop")
                sleep(self._cfg['logging']['frequency'])
        self.shutdown()


def main(argv=None):
    args = parse_args(argv)
    cfg = load_config("config.yml")
    setup_logging(cfg)

    controller = DoorController(cfg, initial_state=args.state, test_mode=args.test)

    def signal_handler(signum, frame):
        controller.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    controller.log_startup()
    controller.run()


if __name__ == '__main__':
    main()
