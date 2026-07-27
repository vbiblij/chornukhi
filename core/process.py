from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from .base_object import BaseObject
from .layer import Layer
from .sim_clock import SimClock


class Process(ABC):
    """
    Abstract process — extended.

    Additions over the original kernel:
        sim_time / wall_time     explicit time split (replaces `time_seconds`)
        parallel_children        flag: when True, children may run in parallel
        parallel_mode            "sequential" | "thread" | "async" (default sequential)
        clock                    optional shared SimClock for deterministic time

    Lifecycle of a step (changes highlighted):
        1. flush pending mutations
        2. for each layer:        before_step(process, dt) -> dt
        3. for each layer:        modify(process, dt, objects)        ← NEW
        4. for each child:        before_child_step, child.step, after_child_step
        5. self._solve(dt)
        6. for each layer:        after_step(process, dt)
        7. update sim_time (+ wall_time if clock is present)

    Backward compatibility:
        - `Layer.modify` defaults to a no-op, so old layers keep working.
        - All other original APIs preserved.
    """

    def __init__(self, name: str | None = None, clock: SimClock | None = None):
        self.name: str = name or self.__class__.__name__
        self.parent: Process | None = None
        self.children: list[Process] = []
        self.layers: list[Layer] = []
        self.objects: list[BaseObject] = []
        self.sim_time: float = 0.0
        self.wall_time: float = 0.0
        self.parallel_children: bool = False
        self.parallel_mode: Literal["sequential", "thread", "async"] = "sequential"
        self.clock: SimClock | None = clock
        self._interrupted: bool = False
        self._is_stepping: bool = False
        self._pending_layer_add: list[Layer] = []
        self._pending_layer_remove: list[Layer] = []
        self._pending_child_add: list[tuple[Process, bool]] = []
        self._pending_child_remove: list[Process] = []

    # Backward-compat alias: old code that read `time_seconds` still works.
    @property
    def time_seconds(self) -> float:
        return self.sim_time

    @property
    def interrupted(self) -> bool:
        return bool(self._interrupted)

    def interrupt(self, recursive: bool = False) -> "Process":
        self._interrupted = True
        if recursive:
            for child in list(self.children):
                child.interrupt(recursive=True)
        return self

    def resume(self, recursive: bool = False) -> "Process":
        self._interrupted = False
        if recursive:
            for child in list(self.children):
                child.resume(recursive=True)
        return self

    def add_object(self, obj: BaseObject) -> BaseObject:
        if obj not in self.objects:
            self.objects.append(obj)
            for layer in list(self.layers):
                layer.on_object_added(self, obj)
            for child in list(self.children):
                child.add_object(obj)
        return obj

    def remove_object(self, obj: BaseObject) -> "Process":
        if obj in self.objects:
            self.objects.remove(obj)
            for child in list(self.children):
                child.remove_object(obj)
        return self

    def add_layer(self, layer: Layer) -> Layer:
        if layer in self.layers or layer in self._pending_layer_add:
            return layer

        if self._is_stepping:
            if layer in self._pending_layer_remove:
                self._pending_layer_remove.remove(layer)
            self._pending_layer_add.append(layer)
            return layer

        self._attach_layer(layer)
        return layer

    def remove_layer(self, layer: Layer) -> "Process":
        if layer not in self.layers and layer not in self._pending_layer_add:
            return self

        if self._is_stepping:
            if layer in self._pending_layer_add:
                self._pending_layer_add.remove(layer)
            elif layer in self.layers and layer not in self._pending_layer_remove:
                self._pending_layer_remove.append(layer)
            return self

        self._detach_layer(layer)
        return self

    def has_layer(self, layer: Layer) -> bool:
        if layer in self._pending_layer_remove:
            return False
        return layer in self.layers or layer in self._pending_layer_add

    def add_child(self, child: "Process", inherit_objects: bool = True) -> "Process":
        if child in self.children or any(c is child for c, _ in self._pending_child_add):
            return child

        if self._is_stepping:
            if child in self._pending_child_remove:
                self._pending_child_remove.remove(child)
            self._pending_child_add.append((child, bool(inherit_objects)))
            return child

        self._attach_child(child, inherit_objects=inherit_objects)
        return child

    def remove_child(self, child: "Process") -> "Process":
        if child not in self.children and child not in self._pending_child_add:
            return self

        if self._is_stepping:
            self._pending_child_add = [(c, inherit) for c, inherit in self._pending_child_add if c is not child]
            if child in self.children and child not in self._pending_child_remove:
                self._pending_child_remove.append(child)
            return self

        self._detach_child(child)
        return self

    def step(self, dt: float) -> None:
        self._flush_pending_mutations()

        if self._interrupted:
            return

        local_dt = max(0.0, float(dt))
        self._is_stepping = True

        try:
            active_layers: list[Layer] = list(self.layers)
            for layer in active_layers:
                local_dt = max(0.0, float(layer.before_step(self, local_dt)))

            # ── NEW: modify hook runs here ────────────────────────────
            for layer in active_layers:
                layer.modify(self, local_dt, list(self.objects))
            # ──────────────────────────────────────────────────────────

            # Child step. Sequential today; parallel path is a future
            # addition that preserves this exact ordering and uses
            # the shared SimClock to keep sim_time deterministic.
            for child in list(self.children):
                child_dt = local_dt
                for layer in active_layers:
                    child_dt = max(0.0, float(layer.before_child_step(self, child, child_dt)))
                child.step(child_dt)
                for layer in active_layers:
                    layer.after_child_step(self, child, child_dt)

            self._solve(local_dt)

            for layer in active_layers:
                layer.after_step(self, local_dt)

            # Advance time. If a shared clock is attached, also tick wall_time.
            if self.clock is not None:
                self.clock.tick(local_dt)
                self.sim_time = self.clock.sim_time
                self.wall_time = self.clock.wall_time
            else:
                self.sim_time += local_dt
        finally:
            self._is_stepping = False
            self._flush_pending_mutations()

    def _attach_layer(self, layer: Layer) -> None:
        self.layers.append(layer)
        layer.on_attach(self)
        for obj in list(self.objects):
            layer.on_object_added(self, obj)

    def _detach_layer(self, layer: Layer) -> None:
        if layer in self.layers:
            self.layers.remove(layer)
            layer.on_detach(self)

    def _attach_child(self, child: "Process", inherit_objects: bool) -> None:
        if child.parent is not None and child.parent is not self:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)
        if inherit_objects:
            for obj in list(self.objects):
                child.add_object(obj)

    def _detach_child(self, child: "Process") -> None:
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def _flush_pending_mutations(self) -> None:
        if self._pending_child_remove:
            pending_remove = self._pending_child_remove[:]
            self._pending_child_remove.clear()
            for child in pending_remove:
                self._detach_child(child)

        if self._pending_layer_remove:
            pending_remove_layers = self._pending_layer_remove[:]
            self._pending_layer_remove.clear()
            for layer in pending_remove_layers:
                self._detach_layer(layer)

        if self._pending_child_add:
            pending_add = self._pending_child_add[:]
            self._pending_child_add.clear()
            for child, inherit_objects in pending_add:
                if child not in self.children:
                    self._attach_child(child, inherit_objects=inherit_objects)

        if self._pending_layer_add:
            pending_add_layers = self._pending_layer_add[:]
            self._pending_layer_add.clear()
            for layer in pending_add_layers:
                if layer not in self.layers:
                    self._attach_layer(layer)

    @abstractmethod
    def _solve(self, dt: float) -> None:
        """Core process logic for one step."""
        raise NotImplementedError
