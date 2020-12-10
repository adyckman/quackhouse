# quackhouse
Managing the quackhouse! (My ducks' home)

This script is for automating a linear actuator using a Raspberry Pi and two mechanical relays.  The linear actuator opens and closes a sliding door to my duckhouse, keeping the little quackers safe inside their home overnight.  The script is multithreaded and utilizes logging.  It determines when to open and close the door based on the position of the Sun in the sky, in turn how much light is outside (the ducks go into their house at about civil twilight, or when the sun is -6 degrees from the visible horizon).  These settings are changeable in config.yml.  Pi settings are going to depend based on your relay setup, I will some day include some more detailed instructions on this.

Basic virtual environment setup:

python3 -m venv quackhouse

source quackhouse/bin/activate

pip install pip --upgrade

pip install -r requirements.txt

Basic usage:

You'll want to change the config.yml file with your desired settings.

Execution:

python3 quackhouse.py --state <Open/Closed> --test

Two simple flags.  --state accepts two values; either Open or Closed.  Case sensitive.  This should be set to whatever the state of the door currently is when you run the script.  When you first execute this script, this value will determine whether the door should immediately open/closed based on the current time and sun position to update how it should be.  The --test flag is useful for monitoring behavior without actually operating the door.

LOCATION:

Latitude and Longitude values must ALWAYS be string values, so ensure single quotes remain there
Elevation is your current elevation in meters.  This value must always be a number value. ensure no quotes are here.  This value isn't incredibly important unless precise time calculations are necessary for your application.

LOGGING:

Generally speaking this will gnaw away at your disk space with status messages that let you track the status of the Sun and your door as the script thinks it.  Frequency controls how long each check should wait before checking again.  Filename should be in the same directory as your executed script.

PI:

This assumes you're using two relays to control the polarity of a DC motor (linear actuator), and as such, which pin controls each relay.  I will provide additional set up for this at a later time.

DOOR:

Duration is how long it takes for your linear actuator to fully open or close the door.  Default is one minute (60 seconds).  Open Elevation and Close Elevation are when you wish the door to open/close.  These values are the elevation of the Sun in degrees; 0 is on the horizon for all intents and purposes; 90 would be directly above you.
