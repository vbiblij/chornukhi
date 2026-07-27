import time
from data import HROMADA_CENTER, SETTLEMENTS
from map_process import MapProcess
import sys

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
