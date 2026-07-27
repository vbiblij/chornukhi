from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence


class Brain(ABC):
    """Decision-making entity.

    A Brain takes a state description and a list of available actions, and
    returns one of them. This is the kernel-level interface for any kind of
    decision-making — classical utility AI, behavior trees, RL policies,
    LLMs, or hybrid compositions.

    Separating decision logic from the layer that applies it means the
    Brain can be unit-tested with arbitrary state/action inputs, swapped
    at runtime, or replaced by a remote model — without touching the
    Process tree.
    """

    @abstractmethod
    def decide(self, state: Any, actions: Sequence[Any]) -> Any:
        """Return one of `actions` (or any value derived from it)."""
        raise NotImplementedError

    def explain(self, state: Any, action: Any) -> str:
        """Optional human-readable explanation of a decision. Default is generic."""
        return f"chose {action}"


class TourBrain(Brain):
    """
    A simple brain that guides a tour through a list of cities, returning to the capital
    after each non-capital city.
    """
    def __init__(self, cities: dict[str, tuple[float, float]], capital_city_name: str = "Kyiv"):
        self.cities = cities
        self.capital_city_name = capital_city_name
        self.tour_sequence = self._build_tour_sequence()
        self.current_step_index = 0

    def _build_tour_sequence(self) -> list[tuple[str, float, float]]:
        sequence = []
        other_cities = [name for name in self.cities if name != self.capital_city_name]
        
        capital_coords = self.cities.get(self.capital_city_name)
        if not capital_coords:
            raise ValueError(f"Capital city '{self.capital_city_name}' not found in provided cities.")
        
        # Add a start point (Kyiv)
        sequence.append((self.capital_city_name, capital_coords[0], capital_coords[1]))

        for city_name in other_cities:
            city_coords = self.cities[city_name]
            sequence.append((city_name, city_coords[0], city_coords[1]))
            # Return to capital after each city
            sequence.append((self.capital_city_name, capital_coords[0], capital_coords[1]))
        
        return sequence

    def decide(self, state: Any, actions: Sequence[Any]) -> dict[str, Any]:
        """
        Returns the next city in the tour sequence.
        The 'state' and 'actions' parameters are not used by this simple brain.
        """
        if not self.tour_sequence:
            # Handle the case where there are no cities in the tour
            return {"city": "End", "lat": None, "lon": None}

        city_data = self.tour_sequence[self.current_step_index]
        self.current_step_index = (self.current_step_index + 1) % len(self.tour_sequence)
        
        return {
            "city": city_data[0],
            "lat": city_data[1],
            "lon": city_data[2],
            "is_capital": city_data[0] == self.capital_city_name
        }

    def explain(self, state: Any, action: Any) -> str:
        return f"Decided to move to {action['city']}."

