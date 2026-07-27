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
