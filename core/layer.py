from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Iterable

from .base_object import BaseObject

if TYPE_CHECKING:
    from .process import Process


class Layer(ABC):
    """
    Base layer — extended.

    New in the enhanced kernel:
        modify(process, dt, objects)
            Runs AFTER before_step and BEFORE child iteration.
            The dedicated hook for read+write logic over a process's objects
            (and/or its children, via `process.children`).
            Replaces the "do everything in before_step" pattern from the
            original kernel.
    """

    def on_attach(self, process: "Process") -> None:
        return

    def on_detach(self, process: "Process") -> None:
        return

    def on_object_added(self, process: "Process", obj: BaseObject) -> None:
        return

    def before_step(self, process: "Process", dt: float) -> float:
        return float(dt)

    # ── NEW ──────────────────────────────────────────────────────────────
    def modify(self, process: "Process", dt: float, objects: list[BaseObject]) -> None:
        """Read+write hook over `process.objects` (children reachable via process.children).

        Runs after before_step, before child iteration and _solve.
        Use this for state preparation; keep it side-effect-light on other layers.
        """
        return
    # ─────────────────────────────────────────────────────────────────────

    def before_child_step(self, parent: "Process", child: "Process", dt: float) -> float:
        return float(dt)

    def after_child_step(self, parent: "Process", child: "Process", dt: float) -> None:
        return

    def after_step(self, process: "Process", dt: float) -> None:
        return
