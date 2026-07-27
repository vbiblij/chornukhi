from data import HROMADA_CENTER, SETTLEMENTS
from flask import Flask, render_template_string, jsonify

# --- Flask App Setup ---
app = Flask(__name__, template_folder='templates')

# --- Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template_string(open('templates/index.html').read())

@app.route('/api/locations')
def get_locations():
    """
    Returns a list of all locations (settlements + hromada center)
    with their name, coordinates, and photo URL.
    """
    # Combine the hromada center and the settlements into a single list
    all_locations = [HROMADA_CENTER] + SETTLEMENTS
    
    # Filter out any locations that might be missing coordinates
    valid_locations = [
        loc for loc in all_locations 
        if loc.get("lat") is not None and loc.get("lng") is not None
    ]

    return jsonify(valid_locations)

if __name__ == "__main__":
    # Standard Flask development server
    app.run(debug=True)
