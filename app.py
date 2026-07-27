import time
from data import HROMADA_CENTER, SETTLEMENTS
import sys
import os
from flask import Flask, Response, render_template_string, jsonify
import threading
from core.process import Process
from core.event_bus import EventBus
from map_process import AnimationProcess
from core.sim_clock import SimClock

# --- Globals for Flask App ---
app = Flask(__name__, template_folder='templates')
event_bus = EventBus()
latest_camera_view = {"lat": 50.45, "lon": 30.52, "zoom": 5}
simulation_status = "Waiting to start..."

simulation_started = threading.Lock()
simulation_started.acquire() # Start in a locked state

def on_camera_view_update(lat: float, lon: float, zoom: int):
    global latest_camera_view
    latest_camera_view = {"lat": lat, "lon": lon, "zoom": zoom}

def on_status_update(status: str):
    global simulation_status
    simulation_status = status

event_bus.subscribe('camera_view_updated', on_camera_view_update)
event_bus.subscribe('simulation_status_updated', on_status_update)
# -----------------------------

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template_string(open('templates/index.html').read())

@app.route('/api/data')
def api_data():
    """Provides camera view and simulation status as JSON."""
    return jsonify(camera=latest_camera_view, status=simulation_status)

@app.route('/start_tour', methods=['POST'])
def start_tour():
    """Starts the simulation tour in a background thread."""
    global simulation_status
    if simulation_started.locked():
        simulation_status = "Starting..."
        simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        simulation_thread.start()
        simulation_started.release()
        return jsonify(message="Tour started!")
    else:
        return jsonify(message="Tour is already running.")

class MapProcess(Process):
    """
    Orchestrates the tour simulation by managing the AnimationProcess.
    """
    def __init__(self, name: str, cities: dict, capital_city_name: str, event_bus: EventBus):
        super().__init__(name=name)
        
        self.event_bus = event_bus

        # The AnimationProcess is the only child process needed.
        # It calculates the camera position and emits events.
        self.animation_process = AnimationProcess(
            name="animation_process",
            event_bus=self.event_bus,
            cities=cities,
            capital_city_name=capital_city_name
        )
        self.add_child(self.animation_process)

        self.clock = SimClock()

    def _solve(self, dt: float) -> None:
        pass

    def shutdown(self):
        """Safely clean up all child processes."""
        self.remove_child(self.animation_process)

def run_simulation():
    # --- Data Preparation ---
    valid_settlements = [s for s in SETTLEMENTS if s["lat"] is not None and s["lng"] is not None]
    tour_cities = {s["name"]: {"lat": s["lat"], "lng": s["lng"]} for s in valid_settlements}
    CAPITAL_CITY = HROMADA_CENTER["name"]
    tour_cities[CAPITAL_CITY] = {"lat": HROMADA_CENTER["lat"], "lng": HROMADA_CENTER["lng"]}

    # --- Simulation Parameters ---
    # Running the simulation at a higher rate for smoother frontend updates
    SIM_DT = 1.0 / 30

    # --- Start Simulation ---
    print(f"Starting map tour simulation for Chornukhy Hromada...")

    map_process = MapProcess(
        name="ChornukhyTour",
        cities=tour_cities,
        capital_city_name=CAPITAL_CITY,
        event_bus=event_bus
    )
    
    # Simulation loop
    start_time = time.time()
    try:
        while not map_process.interrupted:
            map_process.step(SIM_DT)
            # Sleep duration is now shorter for a more responsive simulation loop
            time.sleep(SIM_DT)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"An error occurred during simulation: {e}", file=sys.stderr)
    finally:
        global simulation_status
        simulation_status = "Tour finished. Press Start to run again."
        print("Shutting down simulation thread...")
        # Re-lock to allow the tour to be started again
        if not simulation_started.locked():
             simulation_started.acquire()

if __name__ == "__main__":
    # This block is for local development only.
    # In production, a WSGI server like Gunicorn runs the 'app' object.
    print("Starting Flask development server...")
    app.run(debug=True)
			
