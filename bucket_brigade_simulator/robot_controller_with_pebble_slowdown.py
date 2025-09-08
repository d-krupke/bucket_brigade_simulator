from decimal import Decimal
import fractions

from .pebble import Pebble

from .robot import Robot

from .robot_controller import AbstractRobotController, AbstractRobotControllerFactory


class RobotController(AbstractRobotController):
    def __init__(self, epsilon: fractions.Fraction):
        """
        Robot controller that slows down robots carrying pebbles by a factor epsilon.
        """
        self.epsilon = epsilon

    def begin_event(self, robot: Robot):
        self._changed_direction_in_round = False

    def _invert_direction(self, robot: Robot):
        if not self._changed_direction_in_round:
            robot.invert_direction()
            self._changed_direction_in_round = True

    def end_event(self, robot: Robot):
        pass

    def on_collision_with_robot(
        self,
        robot: Robot,
        own_speed: fractions.Fraction,
        other_robot: Robot,
        other_robots_speed: fractions.Fraction,
    ):
        def sign(x):
            return 1 if x >= 0 else -1

        if (sign(own_speed) != sign(other_robots_speed)) or abs(own_speed) > abs(
            other_robots_speed
        ):
            self._invert_direction(robot)
            for pebble in robot.pebbles:
                robot.drop_pebble(pebble)

    def on_collision_with_pebble(self, robot: Robot, pebble: Pebble):
        robot.take_pebble(pebble)

    def on_collision_with_wall(self, robot: Robot):
        self._invert_direction(robot)
        # print(robot, "hit the wall")

    def on_pebble_drop(self, robot: Robot, pebble: Pebble):
        # print(robot, "dropped", pebble)
        pass

    def on_pebble_take(self, robot: Robot, pebble: Pebble):
        # print(robot, "has taken", pebble)
        pass

    def get_speed(self, robot: Robot) -> fractions.Fraction:
        if robot.pebbles:
            return self.epsilon * robot.get_base_speed()
        else:
            return robot.get_base_speed()


class RobotControllerFactory(AbstractRobotControllerFactory):
    def __init__(self, epsilon: str | float | Decimal = 1.0):
        self.epsilon = fractions.Fraction(epsilon)

    def __call__(self, *args, **kwargs) -> RobotController:
        return RobotController(self.epsilon)
