from .logger import RobotLogger
import matplotlib.pyplot as plt


class CollisionDensityVisualization:
    def __init__(self, logger: RobotLogger):
        self._logger = logger

    def _get_collision_points(self):
        collisions = []
        for robot in self._logger.get_robots():
            collision_log = self._logger.get_collision_log(robot)
            collisions.extend(float(c.position) for c in collision_log)
        return collisions

    def _plot(self, figsize, bins):
        plt.figure(figsize=figsize)
        plt.title("Collision density")
        plt.xlim(0, 1.0)
        plt.hist(self._get_collision_points(), bins=bins)

    def show(self, figsize=None, bins=100):
        self._plot(figsize, bins)
        plt.show()
