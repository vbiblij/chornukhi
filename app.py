import time
from data import HROMADA_CENTER, SETTLEMENTS
from map_process import MapProcess
import sys
from __future__ import annotations
import threading
from flask import Flask, Response, render_template_string, jsonify
from core.process import Process
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.event_bus import EventBus

# Suppress Flask's default startup messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- Globals for Flask App ---
app = Flask(__name__, template_folder='templates')
latest_camera_view = {"lat": 50.45, "lon": 30.52, "zoom": 5}
simulation_status = "Initializing..."
# -----------------------------

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template_string(open('templates/index.html').read())

@app.route('/api/data')
def api_data():
    """Provides camera view and simulation status as JSON."""
    return jsonify(camera=latest_camera_view, status=simulation_status)

class WebServerProcess(Process):
    """
    A process that runs a Flask web server to provide map data via a JSON API.
    """
    def __init__(self, name: str, event_bus: EventBus, host: str = '127.0.0.1', port: int = 5000):
        super().__init__(name=name)
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self.server_thread = None
        
        # Subscribe to events from the simulation
        self.event_bus.subscribe('camera_view_updated', self._on_camera_view_update)
        self.event_bus.subscribe('simulation_status_updated', self._on_status_update)
        print(f" * WebServerProcess initialized. Listening for events.")

    def _on_camera_view_update(self, lat: float, lon: float, zoom: int):
        global latest_camera_view
        latest_camera_view = {"lat": lat, "lon": lon, "zoom": zoom}

    def _on_status_update(self, status: str):
        global simulation_status
        simulation_status = status

    def _solve(self, dt: float) -> None:
        """Starts the Flask server thread on the first step."""
        if self.server_thread is None:
            print(f" * Starting web server on http://{self.host}:{self.port}")
            self.server_thread = threading.Thread(
                target=app.run,
                kwargs={'host': self.host, 'port': self.port, 'debug': False},
                daemon=True
            )
            self.server_thread.start()
    
    def on_detach(self, process: Process) -> None:
        self.event_bus.unsubscribe('camera_view_updated', self._on_camera_view_update)
        self.event_bus.unsubscribe('simulation_status_updated', self._on_status_update)
        # Daemon thread will be terminated automatically.

def main():
    # --- Data Preparation ---
    
    # Filter settlements that have coordinates
    valid_settlements = [s for s in SETTLEMENTS if s["lat"] is not None and s["lng"] is not None]
    
    # Create the dictionary structure needed by the simulation processes
    # { "village_name": {"lat": ..., "lng": ...}, ... }
    tour_cities = {s["name"]: {"lat": s["lat"], "lng": s["lng"]} for s in valid_settlements}
    
    # Add the hromada center to the dictionary
    CAPITAL_CITY = HROMADA_CENTER["name"]
    tour_cities[CAPITAL_CITY] = {"lat": HROMADA_CENTER["lat"], "lng": HROMADA_CENTER["lng"]}

    # --- Simulation Parameters ---
    VIDEO_OUTPUT_FILENAME = "chornukhy_tour.mp4"
    FPS = 24
    SIM_DT = 1.0 / FPS

    # --- Start Simulation ---
    print(f"Found coordinates for {len(valid_settlements)} out of {len(SETTLEMENTS)} villages.")
    print("Only these will be included in the tour.")
    print("-" * 30)
    print(f"Starting map tour simulation for Chornukhy Hromada...")
    print(f"Video will be saved to {VIDEO_OUTPUT_FILENAME}")
    print(f"Please open your web browser to http://127.0.0.1:5000")

    # Create the main map process
    map_process = MapProcess(
        name="ChornukhyTour",
        cities=tour_cities,
        capital_city_name=CAPITAL_CITY,
        video_output_path=VIDEO_OUTPUT_FILENAME,
        fps=FPS
    )

    # Simulation loop
    start_time = time.time()
    try:
        while not map_process.interrupted:
            map_process.step(SIM_DT)
            time.sleep(SIM_DT / 2) # Prevent 100% CPU usage

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"An error occurred during simulation: {e}", file=sys.stderr)
    finally:
        print("Shutting down...")
        map_process.shutdown()
        print(f"Simulation finished. Total run time: {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
