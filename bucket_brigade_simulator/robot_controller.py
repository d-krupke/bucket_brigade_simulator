class AbstractRobotController:
    def begin_event(self, robot):
        raise NotImplementedError()

    def end_event(self, robot):
        raise NotImplementedError()

    def on_collision_with_robot(
        self, robot, own_speed, other_robot, other_robots_speed
    ):
        raise NotImplementedError()

    def on_collision_with_pebble(self, robot, pebble):
        raise NotImplementedError()

    def on_collision_with_wall(self, robot):
        raise NotImplementedError()

    def on_pebble_drop(self, robot, pebble):
        raise NotImplementedError()

    def on_pebble_take(self, robot, pebble):
        raise NotImplementedError()

    def get_speed(self, robot):
        raise NotImplementedError()


class AbstractRobotControllerFactory:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError()
