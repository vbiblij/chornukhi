from data import HROMADA_CENTER, SETTLEMENTS
from flask import Flask, render_template_string, jsonify
from core.brain import TourBrain

# --- Flask App Setup ---
app = Flask(__name__, template_folder='templates')

# --- Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    # The template now contains all the logic for animation.
    return render_template_string(open('templates/index.html').read())

@app.route('/api/tour_sequence')
def get_tour_sequence():
    """
    Generates the full tour sequence and returns it as a JSON object.
    The client-side script will use this data to run the animation.
    """
    # --- Data Preparation ---
    valid_settlements = [s for s in SETTLEMENTS if s["lat"] is not None and s["lng"] is not None]
    tour_cities = {s["name"]: {"lat": s["lat"], "lng": s["lng"]} for s in valid_settlements}
    capital_city_name = HROMADA_CENTER["name"]
    tour_cities[capital_city_name] = {"lat": HROMADA_CENTER["lat"], "lng": HROMADA_CENTER["lng"]}

    # Use the TourBrain to build the sequence of tour stops
    tour_brain_cities = {city_name: (data["lat"], data["lng"]) for city_name, data in tour_cities.items()}
    tour_brain = TourBrain(tour_brain_cities, capital_city_name)
    
    # The sequence from TourBrain includes returns to the capital, which is what we want.
    tour_sequence = tour_brain.tour_sequence

    # Format the sequence into a more descriptive JSON array
    formatted_sequence = [
        {
            "city": city_data[0],
            "lat": city_data[1],
            "lon": city_data[2],
            "is_capital": city_data[0] == capital_city_name
        }
        for city_data in tour_sequence
    ]

    # Define animation parameters that the client will use
    animation_config = {
        "animation_duration": 3.0,  # seconds to move between cities
        "pause_duration": 2.0,      # seconds to pause at each city
        "zoom_level_capital": 14,
        "zoom_level_village": 15
    }

    return jsonify({
        "config": animation_config,
        "sequence": formatted_sequence
    })

if __name__ == "__main__":
    # Standard Flask development server
    app.run(debug=True)
