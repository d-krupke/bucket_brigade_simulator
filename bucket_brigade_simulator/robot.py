import fractions

from .pebble import Pebble

from .robot_controller import AbstractRobotController


class Robot:
    def __init__(
        self, position, speed, controller: AbstractRobotController, id, name, time
    ):
        if (position == 0 and speed < 0) or (position == 1 and speed > 0):
            print("Inverted speed")
            speed *= -1
        self.position = fractions.Fraction(position)
        assert 0 <= self.position <= 1, "Must be between 0 and 1."
        self._speed = fractions.Fraction(speed)
        self.controller: AbstractRobotController = controller
        self.id = int(id)
        self.pebbles = []
        self._time = time
        if name:
            self.name = str(name)
        else:
            self.name = "robot_" + str(self.id)

    def __str__(self):
        return (
            self.name
            + "("
            + str(round(self.position, 5))
            + ", "
            + str(self._speed)
            + ")"
        )

    def get_base_speed(self):
        return self._speed

    def invert_direction(self):
        self._speed *= -1

    def get_time(self):
        return self._time.get_time()

    def get_position(self):
        return self.position

    def get_speed(self):
        if self.controller:
            speed = self.controller.get_speed(self)
        else:
            speed = self._speed
        return speed

    def move(self, time):
        speed = self.get_speed()
        self.position += fractions.Fraction(speed) * fractions.Fraction(time)
        if not 0.0 <= self.position <= 1.0:
            print("Warning: Robot is moving against wall!")
            self.position = min(self.position, fractions.Fraction(1.0))
            self.position = max(self.position, fractions.Fraction(0.0))
        for pebble in self.pebbles:
            pebble.position = self.position
        assert 0.0 <= self.position <= 1.0

    def take_pebble(self, pebble: Pebble):
        assert not pebble.taken
        pebble.taken = self
        self.pebbles.append(pebble)
        if self.controller:
            self.controller.on_pebble_take(self, pebble)

    def drop_pebble(self, pebble: Pebble | None = None):
        """
        If pebble is None, drop the last pebble. Specifying the pebble to drop
        would allow picking up multiple pebbles and dropping them in a different order.
        """
        if pebble is None:
            # select the last pebble by default
            pebble = self.pebbles[-1]
        assert pebble is not None, "No pebble to drop"
        self.pebbles.remove(pebble)
        pebble.taken = None
        if self.controller:
            self.controller.on_pebble_drop(self, pebble)

    def has_pebble(self, p=None):
        if p:
            return p in self.pebbles
        else:
            return len(self.pebbles) > 0

    def on_collision_with_robot(
        self, own_speed: float, other_robot, other_robots_speed: float
    ):
        if self.controller:
            self.controller.on_collision_with_robot(
                self, own_speed, other_robot, other_robots_speed
            )

    def on_collision_with_wall(self):
        if self.controller:
            self.controller.on_collision_with_wall(self)

    def on_collision_with_pebble(self, pebble):
        if self.controller:
            self.controller.on_collision_with_pebble(self, pebble)

    def on_begin_event(self):
        if self.controller:
            self.controller.begin_event(self)

    def on_end_event(self):
        if self.controller:
            self.controller.end_event(self)
