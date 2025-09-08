import unittest

from .robot_controller_with_pebble_slowdown import RobotControllerFactory
from .line_simulator import LineSimulator


class LineSimulatorTest(unittest.TestCase):
    def test_simple_collision(self):
        line = LineSimulator()
        line.set_default_controller_factory(RobotControllerFactory())
        line.create_robot(0.0, 1.0)
        line.create_robot(1.0, -1.0)
        self.assertEqual(line.next_event_in(), 0.5)
        line.create_pebble(0.25)
        self.assertEqual(line.next_event_in(), 0.25)
        self.assertEqual(line.step(), 0.25)
        self.assertEqual(line.robots[0].position, 0.25)
        self.assertEqual(line.step(), 0.25)
        self.assertEqual(line.step(), 0.5)
        line.simulate(5)
