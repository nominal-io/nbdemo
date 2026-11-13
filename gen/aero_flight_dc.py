"""Simulate a one-minute flight over Washington, DC, and write it as ``aero/flight_dc/telemetry.csv``.

Run with ``just gen-flight``. The simulation is seeded and starts at a fixed time, so rerunning it
reproduces the file byte for byte; ``tests/test_generated.py`` checks that. The plane starts at the Lincoln
Memorial and flies east along the National Mall at 50 m/s, climbing to 300 m. After 18 seconds it banks
right by 25 degrees and turns about 180 degrees to fly back west. A light wind from the west pushes it
east, so its ground track differs from its heading.

Adapted from the flight simulation in the nbdemo ``flight_sdr`` notebook.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent.parent / "src" / "nbdemo.data" / "aero" / "flight_dc" / "telemetry.csv"
SEED = 42
START = pd.Timestamp("2026-01-01T12:00:00Z")
DURATION = 60  # seconds
RATE_HZ = 10  # telemetry samples per second
DT = 1 / RATE_HZ
G = 9.81  # m/s^2
LINCOLN_MEMORIAL = (38.8893, -77.0502)  # latitude, longitude
WIND = (4.0, 1.0)  # m/s, toward the east and the north
M_PER_DEG = 111_320.0  # meters per degree of latitude


def generate() -> pd.DataFrame:
    """Return the telemetry, one row per step, indexed by ``time``."""
    rng = np.random.default_rng(SEED)
    steps = int(DURATION * RATE_HZ)
    rows = []
    east = north = 0.0  # meters from the start
    altitude, heading, roll, fuel = 200.0, np.radians(90), 0.0, 80.0  # heading: east
    turned = 0.0
    for step in range(steps):
        t = step * DT
        airspeed = 50 + 0.6 * np.sin(0.4 * t) + rng.normal(0, 0.15)
        # Bank right to turn about 180 degrees, starting at 18 s, then roll out.
        roll_target = np.radians(25) if t >= 18 and turned < np.radians(165) else 0.0
        roll += np.clip(roll_target - roll, -np.radians(10) * DT, np.radians(10) * DT)
        turn_rate = G * np.tan(roll) / airspeed
        heading += turn_rate * DT
        turned += turn_rate * DT
        # Climb to 300 m.
        vertical_speed = np.clip(0.4 * (300 - altitude), -4, 4) + rng.normal(0, 0.1)
        altitude += vertical_speed * DT
        # Air velocity plus wind gives the ground velocity.
        v_east = airspeed * np.sin(heading) + WIND[0]
        v_north = airspeed * np.cos(heading) + WIND[1]
        east += v_east * DT
        north += v_north * DT
        throttle = 62 + 3 * vertical_speed + rng.normal(0, 0.5)
        fuel -= 0.007 * throttle / 65 * DT  # kg
        rows.append(
            {
                "latitude": LINCOLN_MEMORIAL[0] + north / M_PER_DEG,
                "longitude": LINCOLN_MEMORIAL[1] + east / (M_PER_DEG * np.cos(np.radians(LINCOLN_MEMORIAL[0]))),
                "altitude": altitude,
                "heading": np.degrees(heading) % 360,
                "track": np.degrees(np.arctan2(v_east, v_north)) % 360,
                "groundspeed": np.hypot(v_east, v_north),
                "airspeed": airspeed,
                "vertical_speed": vertical_speed,
                "pitch": np.degrees(np.arctan2(vertical_speed, airspeed)) + 2 + rng.normal(0, 0.2),
                "roll": np.degrees(roll) + rng.normal(0, 0.3),
                "throttle": throttle,
                "engine_rpm": 1800 + 8 * throttle + rng.normal(0, 15),
                "fuel": fuel,
                "outside_air_temp": 22 - 0.0065 * altitude + rng.normal(0, 0.05),
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
