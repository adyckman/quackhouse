# quackhouse

Managing the quackhouse! (My ducks' home)

This script automates a linear actuator using a Raspberry Pi and two mechanical relays. The linear actuator opens and closes a sliding door to my duckhouse, keeping the little quackers safe inside their home overnight. The script is multithreaded and utilizes logging. It determines when to open and close the door based on the position of the Sun in the sky — specifically how much light is outside (the ducks go into their house at about civil twilight, or when the sun is -6 degrees from the visible horizon). These settings are changeable in `config.yml`. Pi settings depend on your relay setup; I will some day include more detailed instructions on this.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pip --upgrade
pip install -r requirements.txt
```

## Configuration

Copy or create a `config.yml` file with your desired settings. A template is included in the repo.

### Location

- `latitude` / `longitude` — must be string values (keep single quotes in the YAML)
- `elevation` — your elevation in meters (number, no quotes). Not critical unless precise timing is needed.

### Logging

Status messages that let you track the Sun's position and door state. `frequency` controls how many seconds to wait between checks. `filename` should be in the same directory as the script.

### Pi

Assumes you're using two relays to control the polarity of a DC motor (linear actuator). `forward_pin` and `backward_pin` specify which GPIO pins control each relay.

### Door

- `duration` — how long (in seconds) it takes for your linear actuator to fully open or close the door (default: 60)
- `open_elevation` / `close_elevation` — the Sun's elevation in degrees at which the door should open or close (0 = horizon, 90 = directly overhead)

## Usage

```bash
python3 quackhouse.py --state <Open/Closed> --test
```

- `--state` — the current state of the door when you start the script (`Open` or `Closed`, case-sensitive). On first run, the script will immediately open or close the door based on the current sun position.
- `--test` — run without invoking the Raspberry Pi GPIO pins (useful for monitoring behavior without operating the door)

## Testing

```bash
source .venv/bin/activate
python3 -m pytest test_quackhouse.py -v
```

## Architecture

The core logic lives in the `DoorController` class in `quackhouse.py`:

- **Thread-safe** door status via `threading.Lock`
- **New threads** created per door action (avoids Python's thread-reuse limitation)
- **Graceful shutdown** on SIGINT/SIGTERM
- **Config validation** at startup — catches bad values before the loop starts
- **Conditional GPIO import** — the module can be imported and tested on non-Pi machines
