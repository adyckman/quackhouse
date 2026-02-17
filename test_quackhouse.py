import unittest
from unittest.mock import patch, MagicMock
import threading

from quackhouse import validate_config, DoorController


def make_test_config(**overrides):
    """Return a valid config dict for testing, with optional overrides."""
    cfg = {
        'location': {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'elevation': 10,
        },
        'logging': {
            'level': 'DEBUG',
            'filename': 'test_quackhouse.log',
            'format': '%(asctime)s %(message)s',
            'frequency': 15,
        },
        'pi': {
            'forward_pin': 17,
            'backward_pin': 27,
        },
        'door': {
            'duration': 0.01,
            'open_elevation': 6,
            'close_elevation': -6,
        },
    }
    for key, value in overrides.items():
        section, subkey = key.split('.')
        cfg[section][subkey] = value
    return cfg


class TestValidateConfig(unittest.TestCase):
    def test_valid_config_passes(self):
        cfg = make_test_config()
        validate_config(cfg)  # should not raise

    def test_missing_section_raises(self):
        cfg = make_test_config()
        del cfg['location']
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("Missing config section: 'location'", str(ctx.exception))

    def test_missing_key_raises(self):
        cfg = make_test_config()
        del cfg['door']['duration']
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("Missing config key: 'door.duration'", str(ctx.exception))

    def test_non_numeric_latitude_raises(self):
        cfg = make_test_config(**{'location.latitude': 'add latitude'})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'location.latitude' must be a number", str(ctx.exception))

    def test_non_numeric_longitude_raises(self):
        cfg = make_test_config(**{'location.longitude': 'not a number'})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'location.longitude' must be a number", str(ctx.exception))

    def test_non_numeric_elevation_raises(self):
        cfg = make_test_config(**{'location.elevation': 'high'})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'location.elevation' must be a number", str(ctx.exception))

    def test_zero_frequency_raises(self):
        cfg = make_test_config(**{'logging.frequency': 0})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'logging.frequency' must be a positive number", str(ctx.exception))

    def test_negative_frequency_raises(self):
        cfg = make_test_config(**{'logging.frequency': -5})
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_negative_pin_raises(self):
        cfg = make_test_config(**{'pi.forward_pin': -1})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'pi.forward_pin' must be a non-negative integer", str(ctx.exception))

    def test_float_pin_raises(self):
        cfg = make_test_config(**{'pi.backward_pin': 1.5})
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_zero_duration_raises(self):
        cfg = make_test_config(**{'door.duration': 0})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("'door.duration' must be a positive number", str(ctx.exception))

    def test_open_elevation_not_greater_than_close_raises(self):
        cfg = make_test_config(**{'door.open_elevation': -6, 'door.close_elevation': 6})
        with self.assertRaises(ValueError) as ctx:
            validate_config(cfg)
        self.assertIn("must be greater than", str(ctx.exception))

    def test_equal_elevations_raises(self):
        cfg = make_test_config(**{'door.open_elevation': 5, 'door.close_elevation': 5})
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_non_numeric_open_elevation_raises(self):
        cfg = make_test_config(**{'door.open_elevation': 'high'})
        with self.assertRaises(ValueError):
            validate_config(cfg)


class TestDoorController(unittest.TestCase):
    def setUp(self):
        self.cfg = make_test_config()

    def test_initial_state(self):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        self.assertEqual(ctrl.door_status, 'Closed')
        self.assertIsNone(ctrl._motor)

    def test_initial_state_open(self):
        ctrl = DoorController(self.cfg, initial_state='Open', test_mode=True)
        self.assertEqual(ctrl.door_status, 'Open')

    def test_thread_safe_status(self):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        results = []

        def set_status(value):
            ctrl.door_status = value
            results.append(ctrl.door_status)

        threads = [threading.Thread(target=set_status, args=(s,))
                   for s in ('Opening', 'Open', 'Closing', 'Closed')]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 4)
        # Final status should be one of the valid values
        self.assertIn(ctrl.door_status, ('Opening', 'Open', 'Closing', 'Closed'))

    @patch('quackhouse.sleep')
    def test_open_door_transitions(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        ctrl.open_door()
        self.assertEqual(ctrl.door_status, 'Open')
        mock_sleep.assert_called_with(0.01)

    @patch('quackhouse.sleep')
    def test_close_door_transitions(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Open', test_mode=True)
        ctrl.close_door()
        self.assertEqual(ctrl.door_status, 'Closed')
        mock_sleep.assert_called_with(0.01)

    def test_shutdown_sets_running_false(self):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        ctrl._running = True
        ctrl.shutdown()
        self.assertFalse(ctrl._running)

    def test_test_mode_skips_motor(self):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        self.assertIsNone(ctrl._motor)
        self.assertTrue(ctrl._test_mode)


class TestDoorControllerWithMotor(unittest.TestCase):
    def setUp(self):
        self.cfg = make_test_config()
        self.mock_motor = MagicMock()

    @patch('quackhouse.sleep')
    @patch('quackhouse.Motor')
    def test_open_door_calls_motor(self, MockMotor, mock_sleep):
        MockMotor.return_value = self.mock_motor
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=False)
        ctrl.open_door()
        self.mock_motor.forward.assert_called_once()
        self.mock_motor.stop.assert_called_once()
        self.assertEqual(ctrl.door_status, 'Open')

    @patch('quackhouse.sleep')
    @patch('quackhouse.Motor')
    def test_close_door_calls_motor(self, MockMotor, mock_sleep):
        MockMotor.return_value = self.mock_motor
        ctrl = DoorController(self.cfg, initial_state='Open', test_mode=False)
        ctrl.close_door()
        self.mock_motor.backward.assert_called_once()
        self.mock_motor.stop.assert_called_once()
        self.assertEqual(ctrl.door_status, 'Closed')

    @patch('quackhouse.Motor')
    def test_shutdown_stops_motor(self, MockMotor):
        MockMotor.return_value = self.mock_motor
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=False)
        ctrl._running = True
        ctrl.shutdown()
        self.mock_motor.stop.assert_called_once()
        self.assertFalse(ctrl._running)


class TestMainLoop(unittest.TestCase):
    def setUp(self):
        self.cfg = make_test_config()

    @patch('quackhouse.sleep')
    def test_run_opens_door_when_sun_high(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        call_count = [0]

        def fake_sleep(duration):
            call_count[0] += 1
            if call_count[0] >= 2:
                ctrl._running = False

        mock_sleep.side_effect = fake_sleep

        with patch.object(ctrl, 'sun_altitude', return_value=20.0):
            ctrl.run()

        self.assertEqual(ctrl.door_status, 'Open')

    @patch('quackhouse.sleep')
    def test_run_closes_door_when_sun_low(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Open', test_mode=True)
        call_count = [0]

        def fake_sleep(duration):
            call_count[0] += 1
            if call_count[0] >= 2:
                ctrl._running = False

        mock_sleep.side_effect = fake_sleep

        with patch.object(ctrl, 'sun_altitude', return_value=-20.0):
            ctrl.run()

        self.assertEqual(ctrl.door_status, 'Closed')

    @patch('quackhouse.sleep')
    def test_run_does_nothing_between_thresholds(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)
        call_count = [0]

        def fake_sleep(duration):
            call_count[0] += 1
            if call_count[0] >= 1:
                ctrl._running = False

        mock_sleep.side_effect = fake_sleep

        with patch.object(ctrl, 'sun_altitude', return_value=0.0):
            ctrl.run()

        # Door should remain Closed since sun is between thresholds
        self.assertEqual(ctrl.door_status, 'Closed')

    @patch('quackhouse.sleep')
    def test_run_does_not_reopen_already_open(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Open', test_mode=True)

        def stop_immediately(duration):
            ctrl._running = False

        mock_sleep.side_effect = stop_immediately

        with patch.object(ctrl, 'sun_altitude', return_value=20.0):
            ctrl.run()

        # Door was already open, should stay open (not trigger Opening)
        self.assertEqual(ctrl.door_status, 'Open')

    @patch('quackhouse.sleep')
    def test_run_does_not_reclose_already_closed(self, mock_sleep):
        ctrl = DoorController(self.cfg, initial_state='Closed', test_mode=True)

        def stop_immediately(duration):
            ctrl._running = False

        mock_sleep.side_effect = stop_immediately

        with patch.object(ctrl, 'sun_altitude', return_value=-20.0):
            ctrl.run()

        # Door was already closed, should stay closed
        self.assertEqual(ctrl.door_status, 'Closed')


if __name__ == '__main__':
    unittest.main()
