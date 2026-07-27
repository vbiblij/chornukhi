from __future__ import annotations
import math
from typing import Any, Dict, TYPE_CHECKING
from core.process import Process
from core.brain import TourBrain
from core.sim_clock import SimClock
from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.base_object import BaseObject

class AnimationProcess(Process):
    """
    Calculates camera positions over time and publishes them for other components.
    """
    def __init__(self, name: str, event_bus: EventBus, cities: dict, capital_city_name: str):
        super().__init__(name=name)
        self.event_bus = event_bus
        
        # Transform the input data structure to the one TourBrain expects
        tour_brain_cities = {city_name: (data["lat"], data["lng"]) for city_name, data in cities.items()}
        self.tour_brain = TourBrain(tour_brain_cities, capital_city_name)
        self.decide_call_count = 0
        
        capital = cities[capital_city_name]
        self.current_lat, self.current_lon, self.current_zoom = capital["lat"], capital["lng"], 13

        # Use user-suggested parameters
        self.animation_duration = 3.0 
        self.pause_duration = 3.0 # Increased pause duration

        self.target_lat, self.target_lon, self.target_zoom = self.current_lat, self.current_lon, self.current_zoom
        self.time_in_current_segment = 2.0
        self.state = "initial_pause"
        self.event_bus.publish("simulation_status_updated", status="Tour starting...")

    def _solve(self, dt: float) -> None:
        if self._interrupted:
            return

        self.time_in_current_segment += dt
        
        if self.state == "initial_pause":
             if self.time_in_current_segment >= self.pause_duration:
                self.state = "moving"
                self.time_in_current_segment = 0.0
                self._set_next_target_city()

        elif self.state == "moving":
            self._interpolate_camera()
            if self.time_in_current_segment >= self.animation_duration:
                self.current_lat, self.current_lon, self.current_zoom = self.target_lat, self.target_lon, self.target_zoom
                self.state = "pausing"
                self.time_in_current_segment = 0.0

        elif self.state == "pausing":
            if self.time_in_current_segment >= self.pause_duration:
                self.state = "moving"
                self.time_in_current_segment = 0.0
                self._set_next_target_city()
        
        self.event_bus.publish("camera_view_updated", lat=self.current_lat, lon=self.current_lon, zoom=self.current_zoom)

    def _set_next_target_city(self):
        self.start_lat, self.start_lon, self.start_zoom = self.current_lat, self.current_lon, self.current_zoom
        
        if self.decide_call_count >= len(self.tour_brain.tour_sequence):
            print("Tour finished.")
            self.event_bus.publish("simulation_status_updated", status="Finished. Video saved.")
            self.interrupt(recursive=True)
            if self.parent: self.parent.interrupt(recursive=True)
            return

        next_city_data = self.tour_brain.decide(None, None)
        self.decide_call_count += 1

        self.target_lat, self.target_lon = next_city_data["lat"], next_city_data["lon"]
        
        # Use user-suggested zoom levels
        self.target_zoom = 14 if next_city_data["is_capital"] else 15

        status_message = f"Moving to: {next_city_data['city']}"
        self.event_bus.publish("simulation_status_updated", status=status_message)
        print(status_message)

    def _interpolate_camera(self):
        progress = min(1.0, self.time_in_current_segment / self.animation_duration)
        smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)

        self.current_lat = self.start_lat + (self.target_lat - self.start_lat) * smooth_progress
        self.current_lon = self.start_lon + (self.target_lon - self.start_lon) * smooth_progress
        self.current_zoom = self.start_zoom + (self.target_zoom - self.start_zoom) * smooth_progress
