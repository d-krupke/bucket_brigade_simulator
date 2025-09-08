import json


def get_state_as_json(robots, pebbles):
    robots_json = []
    for robot in robots:
        robots_json.append(
            {
                "name": robot.name,
                "id": robot.id,
                "position": str(robot.position),
                "speed": str(robot.get_speed()),
                "base_speed": str(robot.get_base_speed()),
            }
        )
    pebbles_json = []
    for pebble in pebbles:
        pebbles_json.append(
            {
                "position": str(pebble.position),
                "taken": None if not pebble.taken else pebble.taken.id,
            }
        )
    json_dict = {"robots": robots_json, "pebbles": pebbles_json}
    return json.dumps(json_dict)
