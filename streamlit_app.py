# app.py
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, asdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Tuple

import colorsys
import jinja2
import matplotlib.pyplot as plt
import streamlit as st

from bucket_brigade_simulator.simple import create_simulator_and_logger

# ========= Page setup =========
st.set_page_config(
    page_title="Bucket Brigade Simulator",
    # layout="wide",
    page_icon="🤖",
)
st.title("🤖 Bucket Brigade Simulator")
st.caption(
    "Configure robots & pebbles, then simulate trajectories and watch the animation."
)


# ========= Types =========
@dataclass
class RobotUI:
    name: str
    position: str  # string: allows fractions like "1/10"
    speed: str  # string: allows fractions like "3/20"
    color: str


@dataclass
class PebbleUI:
    id: str
    position: str  # string: allows fractions like "1/4"
    color: str


# ========= Utilities =========
def _rng(seed: int | None) -> random.Random:
    return random.Random(seed) if seed is not None else random


def random_color(rng: random.Random | None = None) -> str:
    rng = rng or random
    h = rng.random()
    s = rng.uniform(0.78, 0.95)  # vivid
    L = rng.uniform(0.45, 0.58)
    r, g, b = colorsys.hls_to_rgb(h, L, s)  # colorsys: HLS
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def sign(x: float) -> int:
    return 1 if x >= 0 else -1


def parse_fraction(expr: str) -> float | None:
    """Parse '1/10', '0.5', '-2/3'. Returns None on failure."""
    expr = (expr or "").strip()
    if not expr:
        return None
    try:
        return float(Fraction(expr))
    except Exception:
        try:
            return float(expr)
        except Exception:
            return None


def _validate_position(expr: str) -> Tuple[bool, str]:
    val = parse_fraction(expr)
    if val is None:
        return False, "Invalid number/fraction"
    if not (0.0 <= val <= 1.0):
        return False, "Must be in [0, 1]"
    return True, ""


def _validate_speed(expr: str) -> Tuple[bool, str]:
    val = parse_fraction(expr)
    if val is None:
        return False, "Invalid number/fraction"
    if not math.isfinite(val) or abs(val) > 10:
        return False, "Speed magnitude too large (|v| ≤ 10)"
    return True, ""


def _validate_epsilon(expr: str) -> Tuple[bool, str]:
    val = parse_fraction(expr)
    if val is None:
        return False, "Invalid number/fraction"
    if val == 0:
        return False, "Cannot be 0"
    if abs(val) > 100:
        return False, "Unusually large; try ≤ 100"
    return True, ""


# ========= Default scenarios (colors generated once per run) =========
def _default_scenarios(seed: int | None) -> Dict[str, Dict[str, Any]]:
    rng = _rng(seed)
    return {
        "Classic 3 Robots": {
            "robots": [
                RobotUI("Robot 1", "1/10", "1/10", random_color(rng)),
                RobotUI("Robot 2", "1/2", "15/20", random_color(rng)),
                RobotUI("Robot 3", "9/10", "3/20", random_color(rng)),
            ],
            "pebbles": [PebbleUI("p0", "1/4", "#f59e0b")],
            "epsilon": "40/41",
            "max_time": 10.0,
        },
        "Single Robot": {
            "robots": [RobotUI("Robot 1", "0.5", "0.1", random_color(rng))],
            "pebbles": [PebbleUI("p0", "0.5", "#f59e0b")],
            "epsilon": "1/2",
            "max_time": 5.0,
        },
        "Two Pebbles": {
            "robots": [
                RobotUI("Robot 1", "0.2", "0.1", random_color(rng)),
                RobotUI("Robot 2", "0.8", "-0.1", random_color(rng)),
            ],
            "pebbles": [
                PebbleUI("p0", "0.3", "#f59e0b"),
                PebbleUI("p1", "0.7", "#8b5cf6"),
            ],
            "epsilon": "1/3",
            "max_time": 8.0,
        },
    }


# ========= Session State =========
def init_state() -> None:
    if "seed" not in st.session_state:
        st.session_state.seed = None  # deterministic palette when set
    if "robots" not in st.session_state:
        rng = _rng(st.session_state.seed)
        st.session_state.robots: List[Dict[str, Any]] = [
            asdict(RobotUI("Robot 1", "1/10", "1/10", random_color(rng))),
            asdict(RobotUI("Robot 2", "1/2", "15/20", random_color(rng))),
            asdict(RobotUI("Robot 3", "9/10", "3/20", random_color(rng))),
        ]
    if "pebbles" not in st.session_state:
        st.session_state.pebbles: List[Dict[str, Any]] = [
            asdict(PebbleUI("p0", "1/4", "#f59e0b"))
        ]
    if "epsilon" not in st.session_state:
        st.session_state.epsilon = "40/41"
    if "max_time" not in st.session_state:
        st.session_state.max_time = 10.0
    if "sim_requested" not in st.session_state:
        st.session_state.sim_requested = True  # auto-run once on load


init_state()


# ========= Template (cached) =========
@st.cache_resource(show_spinner=False)
def load_template() -> jinja2.Template:
    loader = jinja2.FileSystemLoader(searchpath=str(Path(".").resolve()))
    env = jinja2.Environment(loader=loader, autoescape=True)
    return env.get_template("animation.j2.html")


@st.cache_resource(show_spinner=True)
def simulate_and_get_data_cached(cache_key: str):
    """Cache simulator outputs that include non-serializable objects (e.g., logger)."""
    sim, logger = create_simulator_and_logger(epsilon=st.session_state.epsilon)

    # Create entities (keep user’s fractional strings)
    for robot in st.session_state.robots:
        sim.create_robot(
            position=robot["position"], speed=robot["speed"], name=robot["name"]
        )
    for pebble in st.session_state.pebbles:
        sim.create_pebble(position=pebble["position"], name=pebble["id"])

    robot_colors = _robot_color_map_from_session()
    pebble_colors = _pebble_color_map_from_session()

    keyframes: List[Dict[str, Any]] = []
    keyframes.append(_get_timeframe(sim, robot_colors, pebble_colors))

    max_steps = 20_000
    while sim.get_time() < st.session_state.max_time and max_steps > 0:
        sim.step(print_time=False)
        keyframes.append(_get_timeframe(sim, robot_colors, pebble_colors))
        max_steps -= 1

    duration = keyframes[-1]["t"] if keyframes else 0.0
    data = {
        "robots": [
            {"id": r["name"], "label": r["name"], "color": r["color"]}
            for r in st.session_state.robots
        ],
        "pebbles": [
            {"id": p["id"], "color": p.get("color", "#f59e0b")}
            for p in st.session_state.pebbles
        ],
        "keyframes": keyframes,
        "duration": duration,
    }
    return data, logger


template = load_template()

# ========= Sidebar: Scenarios & Settings =========
with st.sidebar:
    st.subheader("Scenarios")
    seed_col1, seed_col2 = st.columns([2, 1])
    with seed_col1:
        seed_str = st.text_input(
            "Palette Seed (optional)",
            value="" if st.session_state.seed is None else str(st.session_state.seed),
            help="Use the same seed to reproduce colors.",
        )
    with seed_col2:
        if st.button("Apply Seed", use_container_width=True):
            try:
                st.session_state.seed = int(seed_str) if seed_str.strip() else None
                # regenerate only colors, keep positions/names
                rng = _rng(st.session_state.seed)
                for r in st.session_state.robots:
                    r["color"] = random_color(rng)
                st.toast("Colors re-seeded")
            except Exception:
                st.warning("Seed must be an integer")

    scenarios = _default_scenarios(st.session_state.seed)
    sel = st.selectbox("Load built-in scenario", list(scenarios.keys()))
    c1, c2 = st.columns(2)
    if c1.button("Load", use_container_width=True):
        s = scenarios[sel]
        st.session_state.robots = [asdict(r) for r in s["robots"]]
        st.session_state.pebbles = [asdict(p) for p in s["pebbles"]]
        st.session_state.epsilon = s["epsilon"]
        st.session_state.max_time = s["max_time"]
        st.session_state.sim_requested = True
        st.rerun()

    # Import / Export
    st.markdown("---")
    st.subheader("Import / Export")
    exp = {
        "robots": st.session_state.robots,
        "pebbles": st.session_state.pebbles,
        "epsilon": st.session_state.epsilon,
        "max_time": st.session_state.max_time,
    }
    st.download_button(
        "⬇️ Export scenario JSON",
        data=json.dumps(exp, indent=2),
        file_name="scenario.json",
        mime="application/json",
        use_container_width=True,
    )
    imp = st.file_uploader("⬆️ Import scenario JSON", type=["json"])
    if imp is not None:
        try:
            payload = json.loads(imp.read().decode("utf-8"))
            st.session_state.robots = payload.get("robots", st.session_state.robots)
            st.session_state.pebbles = payload.get("pebbles", st.session_state.pebbles)
            st.session_state.epsilon = str(
                payload.get("epsilon", st.session_state.epsilon)
            )
            st.session_state.max_time = float(
                payload.get("max_time", st.session_state.max_time)
            )
            st.session_state.sim_requested = True
            st.success("Scenario imported")
        except Exception as e:
            st.error(f"Import failed: {e}")

    st.markdown("---")
    st.subheader("Simulation Settings")
    with st.form("sim_settings_form", clear_on_submit=False):
        epsilon = st.text_input(
            "Epsilon (speed factor while carrying)", value=st.session_state.epsilon
        )
        max_time = st.number_input(
            "Max Time", min_value=0.1, value=float(st.session_state.max_time), step=0.1
        )
        apply_settings = st.form_submit_button("Apply", use_container_width=True)
        if apply_settings:
            st.session_state.epsilon = epsilon
            st.session_state.max_time = float(max_time)
            st.session_state.sim_requested = True
            st.toast("Settings applied")

    if st.button("Reset simulation cache", use_container_width=True):
        simulate_and_get_data_cached.clear()
        st.toast("Simulation cache cleared")


# ========= Editors =========
def robots_editor():
    st.subheader("Robots")
    st.markdown(
        "Positions must be in **[0,1]**. Speeds can be negative or positive fractions (e.g., `-1/5`). "
        "Two robots at the same position is a degenerate case."
    )

    with st.form("robots_form"):
        # header
        hdr = st.columns([5, 5, 5, 2, 1])
        hdr[0].markdown("**Name**")
        hdr[1].markdown("**Position**")
        hdr[2].markdown("**Speed (1/s)**")
        hdr[3].markdown("**Color**")
        hdr[4].markdown(
            "<div style='text-align:center'><b>🗑️</b></div>", unsafe_allow_html=True
        )

        any_invalid = False
        # render rows
        for i, robot in enumerate(st.session_state.robots):
            cols = st.columns([5, 5, 5, 2, 1])
            robot["name"] = cols[0].text_input(
                "Name",
                robot["name"],
                key=f"robot_name_{i}",
                label_visibility="collapsed",
            )
            pos = cols[1].text_input(
                "Position",
                robot["position"],
                key=f"robot_pos_{i}",
                label_visibility="collapsed",
            )
            spd = cols[2].text_input(
                "Speed",
                robot["speed"],
                key=f"robot_speed_{i}",
                label_visibility="collapsed",
            )
            clr = cols[3].color_picker(
                "Color",
                robot["color"],
                key=f"robot_color_{i}",
                label_visibility="collapsed",
            )
            robot["position"], robot["speed"], robot["color"] = pos, spd, clr

            ok_pos, msg_pos = _validate_position(pos)
            ok_spd, msg_spd = _validate_speed(spd)
            if not ok_pos or not ok_spd:
                any_invalid = True
                cols[0].markdown(
                    f"<span style='color:#b45309'>⚠️ {'; '.join([m for ok,m in [(ok_pos,msg_pos),(ok_spd,msg_spd)] if not ok])}</span>",
                    unsafe_allow_html=True,
                )

            # mark for deletion (processed on submit)
            cols[4].checkbox(
                "Delete", key=f"robot_del_{i}", label_visibility="collapsed"
            )

        # two submit buttons in the SAME form
        sub_cols = st.columns([1, 1, 2])
        submitted_add = sub_cols[0].form_submit_button(
            "➕ Add Robot", use_container_width=True
        )
        submitted_apply = sub_cols[1].form_submit_button(
            "✅ Apply changes", use_container_width=True
        )

        # handle actions
        if submitted_add:
            next_num = len(st.session_state.robots) + 1
            rng = _rng(st.session_state.get("seed"))
            st.session_state.robots.append(
                asdict(RobotUI(f"Robot {next_num}", "0.5", "0.1", random_color(rng)))
            )
            st.session_state.sim_requested = False
            st.rerun()

        if submitted_apply:
            # delete checked rows (from end to start)
            to_delete = [
                i
                for i, _ in enumerate(st.session_state.robots)
                if st.session_state.get(f"robot_del_{i}", False)
            ]
            for idx in sorted(to_delete, reverse=True):
                st.session_state.robots.pop(idx)
                # clean up the checkbox key to avoid key collisions on rerender
                st.session_state.pop(f"robot_del_{idx}", None)

            if any_invalid:
                st.warning(
                    "There are invalid robot inputs. Fix them to ensure a meaningful simulation."
                )
            st.session_state.sim_requested = True
            st.rerun()


def pebbles_editor():
    st.subheader("Pebbles")
    st.markdown(
        "Robots carrying a pebble change their speed by factor **epsilon** until next collision."
    )

    with st.form("pebbles_form"):
        hdr = st.columns([6, 5, 2, 1])
        hdr[0].markdown("**Pebble ID**")
        hdr[1].markdown("**Position**")
        hdr[2].markdown("**Color**")
        hdr[3].markdown(
            "<div style='text-align:center'><b>🗑️</b></div>", unsafe_allow_html=True
        )

        any_invalid = False
        for i, pebble in enumerate(st.session_state.pebbles):
            cols = st.columns([6, 5, 2, 1])
            pebble["id"] = cols[0].text_input(
                "ID", pebble["id"], key=f"pebble_id_{i}", label_visibility="collapsed"
            )
            pos = cols[1].text_input(
                "Position",
                pebble["position"],
                key=f"pebble_pos_{i}",
                label_visibility="collapsed",
            )
            clr = cols[2].color_picker(
                "Color",
                pebble.get("color", "#f59e0b"),
                key=f"pebble_color_{i}",
                label_visibility="collapsed",
            )
            pebble["position"], pebble["color"] = pos, clr

            ok_pos, msg = _validate_position(pos)
            if not ok_pos:
                any_invalid = True
                cols[0].markdown(
                    f"<span style='color:#b45309'>⚠️ {msg}</span>",
                    unsafe_allow_html=True,
                )

            cols[3].checkbox(
                "Delete", key=f"pebble_del_{i}", label_visibility="collapsed"
            )

        sub_cols = st.columns([1, 1, 2])
        submitted_add = sub_cols[0].form_submit_button(
            "➕ Add Pebble", use_container_width=True
        )
        submitted_apply = sub_cols[1].form_submit_button(
            "✅ Apply changes", use_container_width=True
        )

        if submitted_add:
            new_id = f"P{len(st.session_state.pebbles)}"
            st.session_state.pebbles.append(asdict(PebbleUI(new_id, "0.5", "#f59e0b")))
            st.session_state.sim_requested = False
            st.rerun()

        if submitted_apply:
            to_delete = [
                i
                for i, _ in enumerate(st.session_state.pebbles)
                if st.session_state.get(f"pebble_del_{i}", False)
            ]
            for idx in sorted(to_delete, reverse=True):
                st.session_state.pebbles.pop(idx)
                st.session_state.pop(f"pebble_del_{idx}", None)

            if any_invalid:
                st.warning(
                    "There are invalid pebble inputs. Fix them for a clean simulation."
                )
            st.session_state.sim_requested = True
            st.rerun()


# ========= Color maps =========
def _robot_color_map_from_session() -> Dict[str, str]:
    return {r["name"]: r["color"] for r in st.session_state.robots}


def _pebble_color_map_from_session() -> Dict[str, str]:
    return {p["id"]: p.get("color", "#f59e0b") for p in st.session_state.pebbles}


# ========= Simulation =========
def _cache_key_from_state() -> str:
    key = {
        "robots": st.session_state.robots,
        "pebbles": st.session_state.pebbles,
        "epsilon": st.session_state.epsilon,
        "max_time": st.session_state.max_time,
    }
    return json.dumps(key, sort_keys=True)


def _get_timeframe(
    sim, robot_colors: Dict[str, str], pebble_colors: Dict[str, str]
) -> Dict[str, Any]:
    t = sim.get_time()
    robots, pebbles = [], []
    for r in sim.robots:
        rob = {
            "id": r.name,
            "x": float(r.position),
            "dir": sign(r.get_speed()),
            "color": robot_colors.get(r.name),
        }
        if r.pebbles:
            rob["carrying"] = r.pebbles[0].name
        robots.append(rob)
    for p in sim.pebbles:
        pebbles.append(
            {
                "id": p.name,
                "x": float(p.position),
                "color": pebble_colors.get(p.name, "#f59e0b"),
            }
        )
    return {"t": float(t), "robots": robots, "pebbles": pebbles}


# ========= Visualization =========
def render_animation(data: Dict[str, Any]) -> None:
    st.subheader("Animation")
    st.markdown("Scroll or scrub the timeline in the embedded player.")
    html = template.render(data=data)
    st.components.v1.html(html, height=390, scrolling=True)


def render_trajectory_plot(data: Dict[str, Any], logger) -> None:
    st.subheader("Trajectory Visualization")

    final_time = data["keyframes"][-1]["t"] if data["keyframes"] else None
    width = 6
    height = min(max(4, (final_time or 4)), 2 * width)

    robot_color_map = {r["id"]: r["color"] for r in data.get("robots", [])}
    pebble_color_map = {p["id"]: p["color"] for p in data.get("pebbles", [])}

    fig = plt.figure(figsize=(width, height))

    # Robots
    for robot in logger.get_robots():
        log = logger.get_position_log(robot)
        times = [entry.time for entry in log]
        positions = [entry.position for entry in log]
        if hasattr(robot, "position") and (
            len(positions) == 0 or positions[-1] != robot.position
        ):
            times.append(
                final_time if final_time is not None else (times[-1] if times else 0)
            )
            positions.append(robot.position)
        color = robot_color_map.get(robot.name)
        plt.plot(
            positions,
            times,
            color=color if isinstance(color, str) and color.startswith("#") else None,
            label=robot.name,
        )

    # Pebbles
    for pebble in logger.get_pebbles():
        log = logger.get_position_log(pebble)
        times = [entry.time for entry in log]
        positions = [entry.position for entry in log]

        last_pos = None
        for kf in reversed(data["keyframes"]):
            for p in kf["pebbles"]:
                if p["id"] == pebble.name:
                    last_pos = p["x"]
                    break
            if last_pos is not None:
                break

        if final_time is not None and last_pos is not None:
            if (
                len(positions) == 0
                or positions[-1] != last_pos
                or times[-1] != final_time
            ):
                times.append(final_time)
                positions.append(last_pos)

        color = pebble_color_map.get(pebble.name)
        plt.plot(
            positions,
            times,
            ".--",
            color=color if isinstance(color, str) and color.startswith("#") else None,
            label=pebble.name,
        )

    plt.xlabel("position")
    plt.ylabel("time")
    plt.title("Robot movement")
    plt.xlim(0, 1)
    plt.ylim(0, None)

    handles, labels = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend(loc="upper right", fontsize="small")

    st.pyplot(fig)
    st.caption("This plot shows the movement of robots and pebbles over time.")


# ========= Main Layout =========
with st.container():
    robots_editor()
    pebbles_editor()
    st.markdown("---")
    # Validation summary + Run button
    ok_eps, msg_eps = _validate_epsilon(st.session_state.epsilon)
    any_bad_robot = any(
        not _validate_position(r["position"])[0] or not _validate_speed(r["speed"])[0]
        for r in st.session_state.robots
    )
    any_bad_pebble = any(
        not _validate_position(p["position"])[0] for p in st.session_state.pebbles
    )

    if not ok_eps:
        st.error(f"Invalid epsilon: {msg_eps}")
    if any_bad_robot or any_bad_pebble:
        st.warning(
            "Some entries are invalid. You can still run, but results may be degenerate."
        )

    run_cols = st.columns([1, 1, 2])
    if run_cols[0].button("▶️ Run Simulation", type="primary", use_container_width=True):
        st.session_state.sim_requested = True
        st.rerun()
    if run_cols[1].button("🧹 Clear All", use_container_width=True):
        st.session_state.robots = []
        st.session_state.pebbles = []
        st.session_state.sim_requested = False
        st.rerun()

    st.markdown("---")
    if not st.session_state.sim_requested:
        st.info("Configure your scenario and click **Run Simulation** to see results.")
    else:
        try:
            cache_key = _cache_key_from_state()
            data, logger = simulate_and_get_data_cached(cache_key)
            kf_count = len(data.get("keyframes", []))
            render_animation(data)
            st.markdown("---")
            colA, colB, colC, colD = st.columns(4)
            colA.metric("Robots", len(data.get("robots", [])))
            colB.metric("Pebbles", len(data.get("pebbles", [])))
            colC.metric("Keyframes", kf_count)
            colD.metric("Duration (s)", f"{data.get('duration', 0.0):.3f}")
            st.markdown("---")
            render_trajectory_plot(data, logger)
        except Exception as e:
            st.exception(e)
            st.error(
                "Simulation failed. Check your inputs (positions in [0,1], reasonable speeds/epsilon)."
            )
