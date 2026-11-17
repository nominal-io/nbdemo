"""Simulate a two-minute flight near Washington, DC, and write it as ``aero/flight_dc/telemetry.csv``.

Run with ``just gen-flight``. The simulation is seeded and starts at a fixed time, so rerunning it
reproduces the file byte for byte; ``tests/test_generated.py`` checks that.

The plane starts at rest on a runway at Reagan National Airport, heading 10 degrees. It accelerates,
rotates at 28 m/s, lifts off and climbs to 300 m. It then flies three banked turns at 25 degrees: 90
degrees right, 120 degrees left and 90 degrees right. A light wind from the west pushes it east once it is
airborne, so its ground track differs from its heading.

Adapted from the flight simulation in the nbdemo ``flight-sdr`` notebook.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent.parent / "src" / "nbdemo" / "data" / "aero" / "flight_dc" / "telemetry.csv"
SEED = 42
START = pd.Timestamp("2026-01-01T12:00:00Z")
DURATION = 120  # seconds
RATE_HZ = 10  # telemetry samples per second
DT = 1 / RATE_HZ
G = 9.81  # m/s^2
RUNWAY = (38.8512, -77.0402)  # latitude, longitude of the start of the roll
RUNWAY_HEADING = 10.0  # degrees clockwise from north
GROUND = 5.0  # field elevation, m
WIND = (4.0, 1.0)  # m/s, toward the east and the north, once airborne
M_PER_DEG = 111_320.0  # meters per degree of latitude

BRAKES_OFF = 3.0  # s: the engine idles until then, then goes to full throttle
ROTATE_SPEED = 28.0  # m/s airspeed at which the nose comes up
CLIMB_SPEED = 45.0  # m/s
CRUISE_SPEED = 50.0  # m/s
CRUISE_ALTITUDE = 300.0  # m
BANK = np.radians(25)
ROLL_RATE = np.radians(10)  # rad/s
# Each turn: start time (s), direction (+1 right, -1 left), degrees
TURNS = [(40.0, 1, 90.0), (62.0, -1, 120.0), (90.0, 1, 90.0)]


def generate() -> pd.DataFrame:
    """Return the telemetry, one row per step, indexed by ``time``."""
    rng = np.random.default_rng(SEED)
    steps = int(DURATION * RATE_HZ)
    rows = []
    east = north = 0.0  # meters from the start of the roll
    altitude, airspeed, vertical_speed = GROUND, 0.0, 0.0
    heading, roll, pitch, fuel = np.radians(RUNWAY_HEADING), 0.0, 0.0, 80.0
    airborne = False
    turn, turned = 0, 0.0  # index of the next or current turn, and the angle turned so far in it
    for step in range(steps):
        t = step * DT
        # Airspeed: idle, then full throttle down the runway, then climb and cruise speeds.
        if t < BRAKES_OFF:
            target, rate, throttle = 0.0, 1.0, 12.0
        elif not airborne:
            target, rate, throttle = 60.0, 2.5, 100.0
        elif altitude < CRUISE_ALTITUDE - 20:
            target, rate, throttle = CLIMB_SPEED, 1.0, 88.0
        else:
            target, rate, throttle = CRUISE_SPEED, 1.0, 62.0
        airspeed += np.clip(target - airspeed, -rate * DT, rate * DT)
        if not airborne and airspeed >= ROTATE_SPEED:
            airborne = True  # the nose comes up and the plane leaves the runway
        # Climb to cruise altitude; the vertical speed builds up over about two seconds after lift-off.
        if airborne:
            wanted = np.clip(0.4 * (CRUISE_ALTITUDE - altitude), -4, 4)
            vertical_speed += np.clip(wanted - vertical_speed, -2 * DT, 2 * DT)
        altitude = max(GROUND, altitude + vertical_speed * DT)
        # Pitch: flat on the runway, then the flight path angle plus a nose-up offset.
        pitch_target = np.degrees(np.arctan2(vertical_speed, max(airspeed, 1.0))) + 2 if airborne else 0.0
        pitch += np.clip(np.radians(pitch_target) - pitch, -np.radians(6) * DT, np.radians(6) * DT)
        # Turns: bank until the turn is almost done, then roll out; wings stay level on the ground.
        roll_target = 0.0
        if airborne and turn < len(TURNS):
            start, direction, degrees = TURNS[turn]
            if t >= start:
                roll_target = direction * BANK
        roll += np.clip(roll_target - roll, -ROLL_RATE * DT, ROLL_RATE * DT)
        turn_rate = G * np.tan(roll) / max(airspeed, 1.0)
        heading += turn_rate * DT
        if roll_target != 0.0:
            turned += abs(turn_rate) * DT
            if turned >= np.radians(degrees) - np.radians(12):  # roll out ahead of the target heading
                turn, turned = turn + 1, 0.0
        # Ground velocity: the plane rolls along the runway, and once airborne the wind pushes it too.
        wind = WIND if airborne else (0.0, 0.0)
        v_east = airspeed * np.sin(heading) + wind[0]
        v_north = airspeed * np.cos(heading) + wind[1]
        east += v_east * DT
        north += v_north * DT
        fuel -= 0.007 * throttle / 65 * DT  # kg
        rows.append(
            {
                "latitude": RUNWAY[0] + north / M_PER_DEG,
                "longitude": RUNWAY[1] + east / (M_PER_DEG * np.cos(np.radians(RUNWAY[0]))),
                "altitude": altitude + (rng.normal(0, 0.1) if airborne else 0.0),
                "heading": np.degrees(heading) % 360,
                "track": np.degrees(np.arctan2(v_east, v_north)) % 360,
                "groundspeed": np.hypot(v_east, v_north),
                "airspeed": airspeed + (rng.normal(0, 0.15) if airspeed > 1 else 0.0),
                "vertical_speed": vertical_speed + (rng.normal(0, 0.1) if airborne else 0.0),
                "pitch": np.degrees(pitch) + rng.normal(0, 0.2),
                "roll": np.degrees(roll) + rng.normal(0, 0.3),
                "throttle": throttle + rng.normal(0, 0.5),
                "engine_rpm": 800 + 19 * throttle + rng.normal(0, 15),
                "fuel": fuel,
                "outside_air_temp": 22 - 0.0065 * (altitude - GROUND) + rng.normal(0, 0.05),
                "bus_voltage": 13.8 + rng.normal(0, 0.03),
            }
        )
    frame = pd.DataFrame(rows, index=START + pd.to_timedelta(np.arange(steps) * DT, unit="s"))
    frame.index.name = "time"
    # Position to about 0.1 m, the rest to four places.
    return frame.round(4).assign(latitude=frame.latitude.round(6), longitude=frame.longitude.round(6))


def to_csv(frame: pd.DataFrame) -> str:
    """Return the CSV text that is written to ``telemetry.csv``."""
    return frame.to_csv(date_format="%Y-%m-%dT%H:%M:%S.%fZ", lineterminator="\n")


def main() -> None:
    """Write ``telemetry.csv``."""
    OUT.write_text(to_csv(generate()))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
