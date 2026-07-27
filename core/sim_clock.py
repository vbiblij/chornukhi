from __future__ import annotations


class SimClock:
    """Deterministic simulation clock.

    Distributes `sim_dt` to children on the same level so that, even when
    children are executed in parallel, they all observe the same simulation
    time. `wall_time` is the real elapsed time, tracked separately.

    Kept as a separate object (rather than baked into Process) so the same
    clock can be shared across a process tree, and so wall-time measurement
    can be swapped (monotonic, perf_counter, mock, etc.) without touching
    Process.
    """

    def __init__(self, start: float = 0.0):
        self._sim_time: float = float(start)
        self._wall_time: float = 0.0

    def tick(self, sim_dt: float, wall_dt: float | None = None) -> float:
        """Advance the clock. Returns the new sim_time."""
        self._sim_time += float(sim_dt)
        if wall_dt is not None:
            self._wall_time += float(wall_dt)
        return self._sim_time

    @property
    def sim_time(self) -> float:
        return self._sim_time

    @property
    def wall_time(self) -> float:
        return self._wall_time
