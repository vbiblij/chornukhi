import time
from data import HROMADA_CENTER, SETTLEMENTS
import sys
from flask import Flask, Response, render_template_string, jsonify
import threading
from core.process import Process
from core.event_bus import EventBus
from map_process import AnimationProcess
from core.sim_clock import SimClock
from utils import FrameBuffer

from layers import MapRenderLayer, VideoRecordLayer

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

class MapProcess(Process):
    """
    Orchestrates the tour simulation, background video recording, and live web server.
    """
    def __init__(self, name: str, cities: dict, capital_city_name: str,
                 video_output_path: str, fps: int):
        super().__init__(name=name)
        
        self.event_bus = EventBus()
        self.frame_buffer = FrameBuffer()

        # Setup layers for background rendering and video recording
        self.map_render_layer = MapRenderLayer(
            event_bus=self.event_bus,
            cities=cities,
            capital_city_name=capital_city_name,
            shared_frame_buffer=self.frame_buffer,
            dpi=100 # Keep DPI reasonable for performance
        )
        self.add_layer(self.map_render_layer)

        # self.video_record_layer = VideoRecordLayer(
        #     output_filepath=video_output_path,
        #     fps=fps,
        #     shared_frame_buffer=self.frame_buffer
        # )
        # self.add_layer(self.video_record_layer)

        # Setup child processes
        self.animation_process = AnimationProcess(
            name="animation_process",
            event_bus=self.event_bus,
            cities=cities,
            capital_city_name=capital_city_name
        )
        self.add_child(self.animation_process)
        
        self.web_server_process = WebServerProcess(
            name="web_server",
            event_bus=self.event_bus
        )
        self.add_child(self.web_server_process)

        self.clock = SimClock()

    def _solve(self, dt: float) -> None:
        pass

    def shutdown(self):
        """Safely clean up all layers and child processes."""
        self.remove_layer(self.map_render_layer)
        # self.remove_layer(self.video_record_layer)
        self.remove_child(self.animation_process)
        self.remove_child(self.web_server_process)


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
