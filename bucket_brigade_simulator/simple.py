from .line_simulator import LineSimulator
from .robot_controller_with_pebble_slowdown import RobotControllerFactory
from .state_extraction import get_state_as_json
from .visualization.logger import RobotControllerFactoryWithLogging


def create_simulator_and_logger(epsilon="1/2"):
    ls = LineSimulator()
    rcf = RobotControllerFactory(epsilon=epsilon)
    rcf = RobotControllerFactoryWithLogging(
        robot_controller_factory=rcf, line_simulator=ls
    )
    ls.set_default_controller_factory(rcf)
    return ls, rcf.get_logger()


def to_json(simulator):
    return get_state_as_json(
        robots=simulator.get_robots(), pebbles=simulator.get_pebbles()
    )
