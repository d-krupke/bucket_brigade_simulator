from decimal import Decimal
import fractions
import functools

from .pebble import Pebble
from .robot import Robot


class SimulationTime:
    def __init__(self):
        self._time = fractions.Fraction(0)

    def get_time(self):
        return self._time

    def increment(self, value):
        assert value > 0
        self._time += value


class LineSimulator:
    def __init__(self):
        self.robots: list[Robot] = []
        self.pebbles: list[Pebble] = []
        self._time = SimulationTime()
        self._id_counter = 0
        self._controller_factory = None
        self._on_robot_creation_callback = None
        self._on_pebble_creation_callback = None
        self._on_step_callback = None

    def _sort_robots(self):
        self.robots.sort(key=lambda r: (r.position, r.get_base_speed()))

    def set_default_controller_factory(self, controller_factory):
        self._controller_factory = controller_factory

    def set_on_robot_creation_callback(self, cb):
        self._on_robot_creation_callback = cb

    def set_on_pebble_creation_callback(self, cb):
        self._on_pebble_creation_callback = cb

    def set_on_step_callback(self, cb):
        """
        :param cb: Callback with signature (LineSimulator)->void
        :return:
        """
        self._on_step_callback = cb

    def get_time(self):
        return self._time.get_time()

    def create_pebble(self, position: str | float | Decimal | fractions.Fraction, name: str|None = None):
        pebble = Pebble(position=position, name=name)
        self.pebbles.append(pebble)
        if self._on_pebble_creation_callback:
            self._on_pebble_creation_callback(pebble)
        return pebble

    def create_robot(self, position, speed, controller=None, name=None) -> Robot:
        if not controller:
            if not self._controller_factory:
                raise ValueError("No controller factory set.")
            controller = self._controller_factory()
        robot = Robot(
            position=position,
            speed=speed,
            controller=controller,
            name=name,
            id=self._id_counter,
            time=self._time,
        )
        self._id_counter += 1
        self.robots.append(robot)
        if self._on_robot_creation_callback:
            self._on_robot_creation_callback(robot)
        return robot

    def _process_inter_robot_collisions(self, speeds):
        for robot, next_robot in self._iterate_robot_pairs():
            if robot.position == next_robot.position:
                robot.on_collision_with_robot(
                    own_speed=speeds[robot],
                    other_robot=next_robot,
                    other_robots_speed=speeds[next_robot],
                )
                next_robot.on_collision_with_robot(
                    own_speed=speeds[next_robot],
                    other_robot=robot,
                    other_robots_speed=speeds[robot],
                )

    def _process_other_collisions(self, pebbles):
        for robot in self.robots:
            for pebble in pebbles:
                # check for pebble is still necessary due to possible double-collisions.
                if (not pebble.taken) and pebble.position == robot.position:
                    robot.on_collision_with_pebble(pebble)
            if not 0 < robot.position < 1:
                robot.on_collision_with_wall()

    def _process_collisions(self, time):
        for robot in self.robots:
            robot.on_begin_event()
        # save the state since callbacks can change things
        pebbles = [p for p in self.pebbles if p.taken is None]
        speeds = {r: r.get_speed() for r in self.robots}
        self._process_other_collisions(pebbles)
        self._process_inter_robot_collisions(speeds)
        for robot in self.robots:
            robot.on_end_event()

    def _process_on_step_callback(self):
        if self._on_step_callback:
            self._on_step_callback(self)

    def step(
        self, print_time: bool = True, max_step: fractions.Fraction | None = None
    ) -> fractions.Fraction:
        if print_time:
            print("Time:", float(self._time.get_time()))
        time = self.next_event_in()
        if time is not None and max_step:
            max_step = fractions.Fraction(max_step)
            time = min(time, max_step)
        assert time is not None and time > 0
        for robot in self.robots:
            robot.move(time)
        self._time.increment(time)
        self._process_collisions(time)
        self._process_on_step_callback()
        return time

    def _iterate_robot_pairs(self):
        for idx, robot in enumerate(self.robots[:-1]):
            next_robot = self.robots[idx + 1]
            yield robot, next_robot

    def simulate(
        self, time=None, print_time=True, max_step: fractions.Fraction | None = None
    ):
        if not time:
            self.step(print_time=print_time, max_step=max_step)
            return
        time = fractions.Fraction(time)
        while time > 0:
            time -= self.step(print_time=print_time, max_step=max_step)

    def _obtain_speed_from_object(self, o):
        try:
            return o.get_speed()
        except AttributeError:
            return fractions.Fraction(0.0)

    def _intersection_time(self, a, b):
        if a.position > b.position:
            a, b = b, a
        if (
            a.position == b.position
        ):  # they are currently colliding. This event already happened.
            return None
        speed_a = self._obtain_speed_from_object(a)
        speed_b = self._obtain_speed_from_object(b)
        if speed_a <= speed_b:
            return None
        return (b.position - a.position) / (speed_a - speed_b)

    def _wall_intersection_time(self, o):
        speed = self._obtain_speed_from_object(o)
        if not 0.0 < o.position < 1.0:
            return 1 / abs(speed)
        if speed == 0:
            return None
        if speed < 0:
            return o.position / abs(speed)
        else:
            return (1 - o.position) / abs(speed)

    def _pebble_intersection_time(self, o):
        intersection_times = (
            self._intersection_time(o, p) for p in self.pebbles if not p.taken
        )
        return min((t for t in intersection_times if t), default=None)

    def _next_robot_collision_event_in(self):
        min_event = None
        for robot, next_robot in self._iterate_robot_pairs():
            collision = self._intersection_time(robot, next_robot)
            if collision:
                min_event = self._robust_min(min_event, collision)
        return min_event

    def _robust_min(self, a, b):
        if not a:
            return b
        if not b:
            return a
        return min(a, b)

    def _next_pebble_or_wall_collision_event_in(self):
        pebble_collision = functools.reduce(
            self._robust_min, (self._pebble_intersection_time(r) for r in self.robots)
        )
        wall_collision = self._robust_min(
            self._wall_intersection_time(self.robots[0]),
            self._wall_intersection_time(self.robots[-1]),
        )
        return self._robust_min(pebble_collision, wall_collision)

    def next_event_in(self):
        self._sort_robots()
        return self._robust_min(
            self._next_robot_collision_event_in(),
            self._next_pebble_or_wall_collision_event_in(),
        )

    def get_robots(self):
        return self.robots

    def get_pebbles(self):
        return self.pebbles
