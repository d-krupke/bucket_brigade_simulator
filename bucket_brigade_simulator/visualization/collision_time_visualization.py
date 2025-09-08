from .logger import RobotLogger
import matplotlib.pyplot as plt


class CollisionTimeVisualization:
    def __init__(self, logger: RobotLogger):
        self.logger = logger

    def _get_collision_times(self, robot, direction=None):
        log = self.logger.get_collision_log(robot)
        if direction:
            log = [log_entry for log_entry in log if log_entry.direction == direction]
        times_of_event = []
        collision_times = []
        for idx, entry in enumerate(log[:-1]):
            next_entry = log[idx + 1]
            times_of_event.append(next_entry.time)
            collision_times.append(next_entry.time - entry.time)
        return times_of_event, collision_times

    def _plot(self, figsize):
        plt.figure(figsize=figsize)
        for robot in self.logger.get_robots():
            times_of_event, collision_times = self._get_collision_times(robot, "right")
            plt.plot(times_of_event, collision_times)

    def show(self, figsize=None):
        self._plot(figsize=figsize)
        plt.show()

    def write(self, path, size=None):
        self._plot(size)
        plt.savefig(path)
