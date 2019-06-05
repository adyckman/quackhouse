# quackhouse
Managing the quackhouse! (My ducks' home)

This script is for automating a linear actuator using a Raspberry Pi and two mechanical relays.  The linear actuator opens and closes a sliding door to my duckhouse, keeping the little quackers safe inside their home overnight.  The script is multithreaded and utilizes logging.  It determines when to open and close the door based on the position of the Sun in the sky, in turn how much light is outside (the ducks go into their house at about civil twilight, or when the sun is -6 degrees from the visible horizon).
