import requests
import json
import re

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Epoch: all bodies fetched at the same point in time
# This must match whatever date you want to simulate from
EPOCH_START = "2000-01-01"
EPOCH_STOP  = "2000-01-02"

# Body definitions: name, JPL Horizons ID, mass (kg), radius (km), rotation speed, tilt
# Mass and radius are physical constants - Horizons doesn't return them easily
BODIES = [
    {"name": "Sun",     "id": "10",     "mass": 1.98841e30, "radius": 695700, "rotation_speed": 1.99362,    "orbital_tilt": 7.25},
    {"name": "Mercury", "id": "199",    "mass": 3.302e23,   "radius": 2439,   "rotation_speed": 0.00302484, "orbital_tilt": 0.035167},
    {"name": "Venus",   "id": "299",    "mass": 4.8685e24,  "radius": 6052,   "rotation_speed": 0.00181095, "orbital_tilt": 177.3},
    {"name": "Earth",   "id": "399",    "mass": 5.97219e24, "radius": 6371,   "rotation_speed": 0.464587,   "orbital_tilt": 23.4392911},
    {"name": "Moon", "id": "301", "mass": 7.342e22, "radius": 1737, "rotation_speed": 0.004627, "orbital_tilt": 5.145},
    {"name": "Mars",    "id": "499",    "mass": 6.4171e23,  "radius": 3390,   "rotation_speed": 0.240282,   "orbital_tilt": 25.19},
    {"name": "Jupiter", "id": "599",    "mass": 1.89819e27, "radius": 69911,  "rotation_speed": 12.29375,   "orbital_tilt": 3.13},
    {"name": "Saturn",  "id": "699",    "mass": 5.6834e26,  "radius": 58232,  "rotation_speed": 9.53734,    "orbital_tilt": 26.73},
    {"name": "Uranus",  "id": "799",    "mass": 8.6813e25,  "radius": 25362,  "rotation_speed": 2.56757,    "orbital_tilt": 97.77},
    {"name": "Neptune", "id": "899",    "mass": 1.02409e26, "radius": 24624,  "rotation_speed": 2.66770,    "orbital_tilt": 28.32},
    {"name": "Pluto",   "id": "999",    "mass": 1.303e22,   "radius": 1188,   "rotation_speed": 0.0,        "orbital_tilt": 122.53},
    {"name": "Halley",  "id": "90000001", "mass": 2.2e14,     "radius": 5,      "rotation_speed": 0.0,        "orbital_tilt": 162.3},
    # --- Dwarf Planets ---
    {"name": "Ceres",    "id": "2000001", "mass": 9.39e20,  "radius": 473,  "rotation_speed": 0.0, "orbital_tilt": 4.0},
    {"name": "Eris",     "id": "136199",  "mass": 1.66e22,  "radius": 1163, "rotation_speed": 0.0, "orbital_tilt": 44.0},
    {"name": "Makemake", "id": "136472",  "mass": 3.1e21,   "radius": 715,  "rotation_speed": 0.0, "orbital_tilt": 29.0},
    {"name": "Haumea",   "id": "136108",  "mass": 4.0e21,   "radius": 780,  "rotation_speed": 0.0, "orbital_tilt": 28.0},
    {"name": "Sedna",    "id": "90377",   "mass": 0.0,      "radius": 497,  "rotation_speed": 0.0, "orbital_tilt": 11.9},

    # --- Comets ---
    {"name": "Hale-Bopp", "id": "90000798", "mass": 1.3e16, "radius": 30, "rotation_speed": 0.0, "orbital_tilt": 89.4},
    {"name": "Encke",     "id": "90000002", "mass": 1.0e13, "radius": 2.4, "rotation_speed": 0.0, "orbital_tilt": 11.8},
]

def fetch_state_vectors(body_id):
    """Fetch position and velocity from JPL Horizons API for a given body."""
    params = {
        "format":      "text",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA":    "NO",
        "MAKE_EPHEM":  "YES",
        "EPHEM_TYPE":  "VECTORS",
        "CENTER":      "'@0'",       # Solar system barycenter
        "START_TIME":  f"'{EPOCH_START}'",
        "STOP_TIME":   f"'{EPOCH_STOP}'",
        "STEP_SIZE":   "'1d'",
        "VEC_TABLE":   "'2'",        # x,y,z,vx,vy,vz
        "CSV_FORMAT":  "YES",        # Easier to parse
    }

    response = requests.get(HORIZONS_URL, params=params)
    if response.status_code != 200:
        print(f"  ERROR: HTTP {response.status_code} for body {body_id}")
        return None

    return response.text

def parse_state_vectors(text):
    """Extract x,y,z,vx,vy,vz from Horizons CSV response text."""
    soe = text.find("$$SOE")
    eoe = text.find("$$EOE")
    if soe == -1 or eoe == -1:
        print("  ERROR: Could not find $$SOE/$$EOE markers in response")
        print(text[:500])  # Print first 500 chars for debugging
        return None

    # The data line is right after $$SOE
    data_section = text[soe + 5 : eoe].strip()
    first_line = data_section.split("\n")[0].strip()

    # CSV fields: JD, blank, date_string, X, Y, Z, VX, VY, VZ, ...
    parts = [p.strip() for p in first_line.split(",")]

    try:
        x  = float(parts[2])
        y  = float(parts[3])
        z  = float(parts[4])
        vx = float(parts[5])
        vy = float(parts[6])
        vz = float(parts[7])
        return x, y, z, vx, vy, vz
    except (IndexError, ValueError) as e:
        print(f"  ERROR parsing line: {first_line}")
        print(f"  Exception: {e}")
        return None

def main():
    results = []
    for body in BODIES:
        # Safety: Ensure required physics constants exist
        mass = body.get("mass", 0.0)
        
        if mass <= 0.0:
            print(f"  SKIPPING {body['name']}: Invalid or zero mass.")
            continue

        print(f"Fetching {body['name']} (id={body['id']})...")
        raw = fetch_state_vectors(body["id"])
        
        vectors = parse_state_vectors(raw) if raw else None
        if not vectors:
            print(f"  FAILED to fetch vectors for {body['name']}")
            continue

        x, y, z, vx, vy, vz = vectors
        
        # Build entry with defaults for safety
        entry = {
            "name":           body["name"],
            "radius":         body.get("radius", 1.0),
            "mass":           mass,
            "px":             x, "py": y, "pz": z,
            "vx":             vx, "vy": vy, "vz": vz,
            "rotation_speed": body.get("rotation_speed", 0.0),
            "orbital_tilt":   body.get("orbital_tilt", 0.0),
        }
        results.append(entry)
    # ... save to file ...

    output_path = "data/solar_system.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nDone! Written {len(results)} bodies to {output_path}")

if __name__ == "__main__":
    main()