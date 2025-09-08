from collections import namedtuple
import fractions

from ..robot_controller import AbstractRobotControllerFactory

from ..robot_controller_with_pebble_slowdown import AbstractRobotController
from ..line_simulator import LineSimulator
from ..robot import Robot
from ..pebble import Pebble


class RobotLogger:
    PositionEntry = namedtuple("PositionEntry", ["time", "position"])
    PebbleEntry = namedtuple(
        "PebbleEntry", ["time", "position", "pebble", "action", "robot"]
    )
    CollisionEntry = namedtuple(
        "CollisionEntry", ["time", "position", "with_robot", "direction"]
    )

    def __init__(self, simulator: LineSimulator):
        self._simulator = simulator
        for pebble in self._simulator.pebbles:
            self.set_initial_pebble_position(pebble)
        for robot in self._simulator.robots:
            self.set_initial_robot_position(robot)
        simulator.set_on_pebble_creation_callback(self.set_initial_pebble_position)
        simulator.set_on_robot_creation_callback(self.set_initial_robot_position)
        self._position_log: dict[Robot | Pebble, list[RobotLogger.PositionEntry]] = (
            dict()
        )
        self._collision_log: dict[Robot, list[RobotLogger.CollisionEntry]] = dict()
        self._pebble_log: dict[Robot | Pebble, list[RobotLogger.PebbleEntry]] = dict()

    def get_robots(self) -> list[Robot]:
        return self._simulator.robots

    def get_pebbles(self) -> list[Pebble]:
        return self._simulator.pebbles

    def get_position_log(self, object: Robot | Pebble):
        return self._position_log[object]

    def get_collision_log(self, robot: Robot):
        return self._collision_log[robot]

    def get_pebble_log(self, robot_or_pebble: Robot | Pebble):
        return self._pebble_log[robot_or_pebble]

    def set_initial_robot_position(self, robot: Robot):
        self._position_log[robot] = [
            RobotLogger.PositionEntry(
                position=robot.position, time=self._simulator.get_time()
            )
        ]
        self._collision_log[robot] = []
        self._pebble_log[robot] = []

    def set_initial_pebble_position(self, pebble: Pebble):
        self._position_log[pebble] = [
            RobotLogger.PositionEntry(
                position=pebble.position, time=self._simulator.get_time()
            )
        ]
        self._pebble_log[pebble] = []

    def log_robot_position(self, robot: Robot):
        self._position_log[robot].append(
            RobotLogger.PositionEntry(
                position=robot.position, time=self._simulator.get_time()
            )
        )
        for pebble in robot.pebbles:
            self._position_log[pebble].append(
                RobotLogger.PositionEntry(
                    position=pebble.position, time=self._simulator.get_time()
                )
            )

    def log_pebble_drop(self, robot: Robot, pebble: Pebble):
        self._position_log[pebble].append(
            RobotLogger.PositionEntry(
                position=pebble.position, time=self._simulator.get_time()
            )
        )
        pe = RobotLogger.PebbleEntry(
            time=self._simulator.get_time(),
            position=pebble.position,
            pebble=pebble,
            action="drop",
            robot=robot,
        )
        self._pebble_log[robot].append(pe)
        self._pebble_log[pebble].append(pe)

    def log_pebble_take(self, robot: Robot, pebble: Pebble):
        self._position_log[pebble].append(
            RobotLogger.PositionEntry(
                position=pebble.position, time=self._simulator.get_time()
            )
        )
        pe = RobotLogger.PebbleEntry(
            time=self._simulator.get_time(),
            position=pebble.position,
            pebble=pebble,
            action="take",
            robot=robot,
        )
        self._pebble_log[robot].append(pe)
        self._pebble_log[pebble].append(pe)

    def log_robot_collision(self, robot: Robot, with_robot: Robot, direction):
        self._collision_log[robot].append(
            RobotLogger.CollisionEntry(
                time=self._simulator.get_time(),
                with_robot=with_robot,
                position=robot.position,
                direction=direction,
            )
        )


class RobotControllerLoggingWrapper(AbstractRobotController):
    def __init__(self, controller: AbstractRobotController, logger: RobotLogger):
        self.controller: AbstractRobotController = controller
        self._logger: RobotLogger = logger
        self._speed: fractions.Fraction | None = None

    def on_collision_with_pebble(self, robot: Robot, pebble: Pebble):
        self.controller.on_collision_with_pebble(robot, pebble)
        self._logger.log_robot_position(robot)

    def on_collision_with_robot(
        self,
        robot: Robot,
        own_speed: fractions.Fraction,
        other_robot: Robot,
        other_robots_speed: fractions.Fraction,
    ):
        self.controller.on_collision_with_robot(
            robot, own_speed, other_robot, other_robots_speed
        )
        self._logger.log_robot_position(robot)
        assert self._speed is not None, "Speed should have been set in begin_event"
        if self._speed < other_robots_speed:
            direction = "right"
        else:
            direction = "left"
        self._logger.log_robot_collision(robot, other_robot, direction)

    def on_collision_with_wall(self, robot: Robot):
        self.controller.on_collision_with_wall(robot)
        self._logger.log_robot_position(robot)

    def on_pebble_take(self, robot: Robot, pebble: Pebble):
        self.controller.on_pebble_take(robot, pebble)
        self._logger.log_robot_position(robot)
        self._logger.log_pebble_take(robot, pebble)

    def on_pebble_drop(self, robot: Robot, pebble: Pebble):
        self.controller.on_pebble_drop(robot, pebble)
        self._logger.log_robot_position(robot)
        self._logger.log_pebble_drop(robot, pebble)

    def get_speed(self, robot: Robot):
        return self.controller.get_speed(robot)

    def begin_event(self, robot: Robot):
        self.controller.begin_event(robot)
        self._speed = robot.get_speed()

    def end_event(self, robot: Robot):
        self.controller.end_event(robot)
        self._speed = None


class RobotControllerFactoryWithLogging:
    def __init__(
        self,
        robot_controller_factory: AbstractRobotControllerFactory,
        line_simulator: LineSimulator,
    ):
        self._robot_controller_factory = robot_controller_factory
        self.logger = RobotLogger(line_simulator)

    def get_logger(self) -> RobotLogger:
        return self.logger

    def __call__(self, *args, **kwargs):
        return RobotControllerLoggingWrapper(
            self._robot_controller_factory(), self.logger
        )
