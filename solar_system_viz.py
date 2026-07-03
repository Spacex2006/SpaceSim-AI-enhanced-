"""
Reads data/simulation_output.csv and generates a single self-contained
solar_system_viewer.html you can open directly in a browser.

Usage:
    python3 build_viewer.py [path/to/simulation_output.csv] [output.html]
"""
import sys
import json
import base64
import numpy as np
import pandas as pd

# =====================================================================
# CLI args
# =====================================================================
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/simulation_output.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "solar_system_viewer.html"

# =====================================================================
# 1. Load data
# =====================================================================
print(f"Loading {CSV_PATH} ...")
df = pd.read_csv(CSV_PATH)

required_cols = {"step", "body_id", "x", "y", "z"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"CSV is missing required columns: {missing}")

df["step"] = df["step"].astype(int)
df["body_id"] = df["body_id"].astype(int)
df["x"] = pd.to_numeric(df["x"], errors='coerce')
df["y"] = pd.to_numeric(df["y"], errors='coerce')
df["z"] = pd.to_numeric(df["z"], errors='coerce')

clean_df = df.dropna(subset=["x", "y", "z"]).copy()

names = {
    0: "Sun", 1: "Mercury", 2: "Venus", 3: "Earth", 4: "Moon", 5: "Mars",
    6: "Jupiter", 7: "Saturn", 8: "Uranus", 9: "Neptune", 10: "Pluto",
    11: "Halley", 12: "Ceres", 13: "Eris", 14: "Makemake", 15: "Haumea",
    16: "Sedna", 17: "Hale-Bopp", 18: "Encke",
}

color_hex = {
    0: "#ffd34d", 1: "#9a9a9a", 2: "#e8a34d", 3: "#4dc9ff", 4: "#c9c9c9",
    5: "#e05a3f", 6: "#c98a55", 7: "#e6cc8a", 8: "#7fc9ff", 9: "#4d6de0",
    10: "#e8e8e8", 11: "#7dffb3", 12: "#a9d3ff", 13: "#d0a9ff", 14: "#ffb3d9",
    15: "#ff9a9a", 16: "#ff9a4d", 17: "#8affd9", 18: "#a9ff7d",
}

real_radius_km = {
    0: 696000, 1: 2440, 2: 6052, 3: 6371, 4: 1737, 5: 3390,
    6: 69911, 7: 58232, 8: 25362, 9: 24622, 10: 1188,
    11: 5, 12: 470, 13: 1163, 14: 715, 15: 780, 16: 500,
    17: 60, 18: 2.4,
}

unique_bodies = sorted(int(b) for b in clean_df["body_id"].unique())
all_steps = sorted(clean_df["step"].unique())
if not all_steps:
    raise ValueError("No valid steps found in the data.")
print(f"Found {len(unique_bodies)} bodies and {len(all_steps)} simulation steps.")

# =====================================================================
# 2. Coordinate scale engine
# =====================================================================
sun_rows = clean_df[clean_df.body_id == 0]
earth_rows = clean_df[clean_df.body_id == 3]

if not sun_rows.empty and not earth_rows.empty:
    s0, e0 = sun_rows.iloc[0], earth_rows.iloc[0]
    earth_sun_dist = float(np.sqrt((e0.x - s0.x) ** 2 + (e0.y - s0.y) ** 2 + (e0.z - s0.z) ** 2))
else:
    earth_sun_dist = float(clean_df[["x", "y", "z"]].abs().to_numpy().max())
if earth_sun_dist <= 0 or np.isnan(earth_sun_dist):
    earth_sun_dist = 1.0

TARGET_EARTH_ORBIT_UNITS = 100.0
COORD_SCALE = TARGET_EARTH_ORBIT_UNITS / earth_sun_dist

sun_mean = sun_rows[["x", "y", "z"]].mean() if not sun_rows.empty else pd.Series({"x": 0.0, "y": 0.0, "z": 0.0})
body_mean_dist_scaled = {}
for b in unique_bodies:
    bdf = clean_df[clean_df.body_id == b]
    d = np.sqrt((bdf.x - sun_mean.x) ** 2 + (bdf.y - sun_mean.y) ** 2 + (bdf.z - sun_mean.z) ** 2)
    body_mean_dist_scaled[b] = float(d.mean()) * COORD_SCALE

non_sun_dists = sorted(v for k, v in body_mean_dist_scaled.items() if k != 0 and v > 0)
innermost_dist = non_sun_dists[0] if non_sun_dists else 10.0

# Define a single global scaling factor
# Lowering this number makes ALL planets smaller proportionally
GLOBAL_RADIUS_SCALAR = 0.000005 

def visual_radius(body_id):
    # Get the raw proportional size
    raw_size = real_radius_km.get(body_id, 500) * COORD_SCALE * GLOBAL_RADIUS_SCALAR
    
    # Define a minimum floor for visibility (e.g., 0.5 units)
    # This prevents the Moon from being a sub-pixel speck
    min_size = 0.5
    
    # Enforce the floor
    return max(raw_size, min_size)


# =====================================================================
# 3. Static orbit paths (Dense, un-strided for perfect circles)
# =====================================================================
orbit_data = {}  
MAX_ORBIT_POINTS = 75000 

for b in unique_bodies:
    body_df = clean_df[clean_df.body_id == b].sort_values("step")
    if len(body_df) < 2:
        continue
    
    body_df = body_df.head(MAX_ORBIT_POINTS)
        
    pts = np.empty((len(body_df), 3), dtype=np.float32)
    pts[:, 0] = body_df.x.to_numpy() * COORD_SCALE
    pts[:, 1] = body_df.z.to_numpy() * COORD_SCALE  
    pts[:, 2] = body_df.y.to_numpy() * COORD_SCALE
    orbit_data[b] = pts.flatten()

# =====================================================================
# 4. Animation keyframes 
# =====================================================================
MAX_ANIM_FRAMES = 15000
frame_step = max(1, len(all_steps) // MAX_ANIM_FRAMES)
anim_steps = all_steps[:15000]
n_frames = len(anim_steps)
print(f"Animation: {n_frames} keyframes (every {frame_step} step(s) of {len(all_steps)} total).")

body_index = {b: i for i, b in enumerate(unique_bodies)}
n_bodies = len(unique_bodies)
frame_positions = np.zeros((n_frames, n_bodies, 3), dtype=np.float32)

last_known_pos = {}
df_indexed = clean_df.set_index(["step", "body_id"]).sort_index()

for b in unique_bodies:
    first_row = clean_df[clean_df.body_id == b].iloc[0]
    last_known_pos[b] = [first_row["x"] * COORD_SCALE, first_row["z"] * COORD_SCALE, first_row["y"] * COORD_SCALE]

for fi, s in enumerate(anim_steps):
    try:
        sub = df_indexed.loc[s]
    except KeyError:
        for b in unique_bodies:
            bi = body_index[b]
            frame_positions[fi, bi, :] = last_known_pos[b]
        continue
        
    if isinstance(sub, pd.Series):
        sub = sub.to_frame().T
        
    for b in unique_bodies:
        bi = body_index[b]
        if b in sub.index:
            row = sub.loc[b]
            x_v = float(row["x"]) * COORD_SCALE
            z_v = float(row["z"]) * COORD_SCALE
            y_v = float(row["y"]) * COORD_SCALE
            
            if np.isnan(x_v) or np.isnan(z_v) or np.isnan(y_v):
                frame_positions[fi, bi, :] = last_known_pos[b]
            else:
                last_known_pos[b] = [x_v, z_v, y_v]
                frame_positions[fi, bi, 0] = x_v
                frame_positions[fi, bi, 1] = z_v
                frame_positions[fi, bi, 2] = y_v
        else:
            frame_positions[fi, bi, :] = last_known_pos[b]

for bi in range(n_bodies):
    pos_df = pd.DataFrame(frame_positions[:, bi, :], columns=["x", "y", "z"])
    pos_df = pos_df.ffill().bfill().fillna(0.0)
    frame_positions[:, bi, :] = pos_df.to_numpy(dtype=np.float32)

frame_positions = np.nan_to_num(frame_positions, nan=0.0, posinf=0.0, neginf=0.0)

max_extent = max(
    float(clean_df["x"].abs().max()) * COORD_SCALE,
    float(clean_df["y"].abs().max()) * COORD_SCALE,
)

major_planet_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
major_df = clean_df[clean_df.body_id.isin(major_planet_ids)]
if not major_df.empty:
    major_planet_limit = max(major_df["x"].abs().max(), major_df["y"].abs().max()) * COORD_SCALE * 1.15
else:
    major_planet_limit = max_extent

# =====================================================================
# 5. Encode compactly
# =====================================================================
def b64_f32(arr):
    return base64.b64encode(np.asarray(arr, dtype=np.float32).tobytes()).decode("ascii")

bodies_meta = []
for b in unique_bodies:
    bodies_meta.append({
        "id": int(b),
        "name": names.get(b, f"Body {b}"),
        "color": color_hex.get(b, "#ffffff"),
        "radius": float(visual_radius(b)),
        "orbit": b64_f32(orbit_data[b]) if b in orbit_data else "",
    })

anim_payload = {
    "steps": [int(s) for s in anim_steps],
    "bodyOrder": [int(b) for b in unique_bodies],
    "positions": b64_f32(frame_positions.flatten()),
    "nFrames": int(n_frames),
    "nBodies": int(n_bodies),
}

data_json = json.dumps({
    "bodies": bodies_meta,
    "anim": anim_payload,
    "maxExtent": max_extent,
    "majorPlanetLimit": major_planet_limit,
    "earthOrbitUnits": TARGET_EARTH_ORBIT_UNITS,
})

print(f"Payload size: {len(data_json)/1e6:.2f} MB")

# =====================================================================
# 6. HTML Payload
# =====================================================================
HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solar System Viewer</title>
<style>
  @font-face {
    font-family: 'Viewer Mono';
    src: local('JetBrains Mono'), local('SF Mono'), local('Menlo'), local('Consolas');
  }
  :root {
    --amber: #ffb300;
    --amber-dim: #a56f00;
    --bg: #010203;
    --panel: rgba(6, 9, 12, 0.82);
    --line: rgba(255, 179, 0, 0.18);
    --text: #d9dde1;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); overflow: hidden; height: 100%; }
  body {
    font-family: 'Viewer Mono', ui-monospace, 'SF Mono', 'Cascadia Code', monospace;
    color: var(--text);
  }
  #scene { position: fixed; inset: 0; }

  #hud {
    position: fixed; top: 14px; left: 14px;
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 10px 14px;
    font-size: 11px; line-height: 1.7;
    letter-spacing: 0.02em;
    min-width: 200px;
    backdrop-filter: blur(4px);
    pointer-events: none;
    z-index: 50;
  }
  #hud .row { display: flex; justify-content: space-between; gap: 16px; }
  #hud .label { color: #777d84; }
  #hud .val { color: var(--amber); }
  #hud .title { color: var(--text); font-size: 12px; letter-spacing: 0.08em; margin-bottom: 6px; text-transform: uppercase; opacity: 0.85;}

  #help {
    position: fixed; top: 14px; right: 14px;
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 10px 14px;
    font-size: 10.5px; line-height: 1.8;
    color: #9099a1;
    text-align: right;
    pointer-events: none;
    z-index: 50;
  }
  #help b { color: var(--amber); font-weight: 500; }

  #legend {
    position: fixed; top: 14px; right: 14px;
    margin-top: 105px;
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 8px 12px;
    font-size: 10.5px;
    max-height: 60vh;
    overflow-y: auto;
    display: block;
    z-index: 50;
  }
  #legend .item { display: flex; align-items: center; gap: 8px; padding: 3px 0; white-space: nowrap; transition: opacity 0.2s; }
  #legend .item:hover { color: var(--amber); }
  #legend .sw { width: 8px; height: 8px; border-radius: 50%; flex: none; cursor: pointer; }
  #legend .name { cursor: pointer; flex: 1; }

  #bottom {
    position: fixed; left: 0; right: 0; bottom: 0;
    background: var(--panel);
    border-top: 1px solid var(--line);
    padding: 10px 18px 14px;
    backdrop-filter: blur(4px);
    z-index: 50;
  }
  #timeline {
    -webkit-appearance: none; appearance: none;
    width: 100%; height: 3px; background: #2a2f34;
    outline: none; margin: 10px 0 4px;
  }
  #timeline::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 11px; height: 11px; border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 8px var(--amber);
    cursor: pointer;
    margin-top: -4px;
  }
  #timeline::-moz-range-thumb {
    width: 11px; height: 11px; border-radius: 50%;
    background: var(--amber); border: none;
    box-shadow: 0 0 8px var(--amber); cursor: pointer;
  }
  #timeline::-webkit-slider-runnable-track { height: 3px; background: #2a2f34; }

  #controls-row { display: flex; align-items: center; gap: 14px; font-size: 11px; }
  button.ctl {
    background: transparent; border: 1px solid var(--line); color: var(--text);
    font-family: inherit; font-size: 12px; padding: 5px 11px; cursor: pointer;
    letter-spacing: 0.05em;
  }
  button.ctl:hover { border-color: var(--amber); color: var(--amber); }
  button.ctl.active { border-color: var(--amber); color: var(--amber); background: rgba(255,179,0,0.08); }
  #speedGroup { display: flex; gap: 4px; }
  #stepLabel { color: #9099a1; min-width: 190px; }
  #stepLabel b { color: var(--amber); font-weight: 500; }

  #loading {
    position: fixed; inset: 0; background: #030405; z-index: 999;
    display: flex; align-items: center; justify-content: center;
    color: var(--amber); font-size: 12px; letter-spacing: 0.1em;
  }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-thumb { background: var(--amber-dim); }
</style>
</head>
<body>
<div id="loading">DECODING TRAJECTORY DATA&hellip;</div>
<div id="scene"></div>

<div id="hud">
  <div class="title">Telemetry</div>
  <div class="row"><span class="label">Bodies</span><span class="val" id="hudBodies">—</span></div>
  <div class="row"><span class="label">Scale</span><span class="val" id="hudScale">1 AU &asymp; 100u</span></div>
</div>

<div id="help">
  <b>drag</b> orbit &middot; <b>scroll</b> zoom &middot; <b>right-drag</b> pan<br>
  <b>click planet or legend name</b> to follow target<br>
  <b>click empty space</b> to release lock<br>
  <b>space</b> play/pause
</div>

<div id="legend"></div>

<div id="bottom">
  <div id="controls-row">
    <button class="ctl" id="playBtn">&#9654; Play</button>
    <div id="speedGroup"></div>
    <span id="stepLabel">
      step <b id="stepNow">0</b> / <span id="stepTotal">0</span> &nbsp;|&nbsp; 
      Year: <b id="yearNow">2000.00</b>
    </span>
    <span style="flex:1"></span>
    <button class="ctl" id="fitBtn">Fit view</button>
  </div>
  <input type="range" id="timeline" min="0" max="1000" value="0" step="1">
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module">
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const DATA = __DATA_JSON__;

function decodeF32(b64) {
  if (!b64) return new Float32Array(0);
  const bin = atob(b64);
  const buf = new ArrayBuffer(bin.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
  return new Float32Array(buf);
}

const bodies = DATA.bodies.map(b => ({
  ...b,
  orbitPts: decodeF32(b.orbit),
}));
const animPositions = decodeF32(DATA.anim.positions);
const nFrames = DATA.anim.nFrames;
const nBodies = DATA.anim.nBodies;
const bodyOrder = DATA.anim.bodyOrder;
const stepsArr = DATA.anim.steps;

function framePos(frame, bi, out) {
  const base = (frame * nBodies + bi) * 3;
  out.set(animPositions[base], animPositions[base + 1], animPositions[base + 2]);
}

// -----------------------------------------------------------------
// Scene setup
// -----------------------------------------------------------------
const mount = document.getElementById('scene');
const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1e11);
const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
mount.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.rotateSpeed = 0.5;
controls.zoomSpeed = 0.9;
controls.minDistance = 0.01;
controls.maxDistance = 1e10;

scene.add(new THREE.AmbientLight(0xffffff, 2.5));
const sunLight = new THREE.PointLight(0xffffff, 3.0, 0, 0); 
scene.add(sunLight);

// =================================================================
// REAL NIGHT SKY BACKDROP
// An actual equirectangular all-sky photograph (Solar System Scope /
// NASA imagery, CC-BY 4.0) mapped onto a huge inverted sphere, instead
// of randomly scattered fake points. Astronomically this is a
// reasonable stand-in for "the sky as seen from Earth": stars are so
// far away that parallax across the entire solar system is far too
// small to see, so one fixed backdrop centered on the Sun looks
// correct from any planet's vantage point, Earth included.
// =================================================================
{
  const skyRadius = Math.max(DATA.maxExtent * 12, 500000);
  const geo = new THREE.SphereGeometry(skyRadius, 64, 64);

  // Flat dark fallback shown immediately, and kept if the texture can't
  // load (e.g. viewing this file offline with no internet access).
  const skyMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0x02030a, side: THREE.BackSide }));
  scene.add(skyMesh);

  new THREE.TextureLoader().load(
    'stars_milky_way_8k.jpg',
    (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.wrapS = THREE.RepeatWrapping;
      skyMesh.material.dispose();
      skyMesh.material = new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide });
    },
    undefined,
    () => { /* file missing - keep the flat dark fallback */ }
  );
}

const meshes = {};
const hitMeshes = {}; 
const staticLines = {};
const trailLines = {};
const pathVisible = {};
const orbitIndices = {}; 
let followId = null; 
const tmpV = new THREE.Vector3();

const labelDiv = {};
const labelLayer = document.createElement('div');
labelLayer.style.cssText = 'position:fixed;inset:0;pointer-events:none;overflow:hidden;';
document.body.appendChild(labelLayer);

const trailGeometries = {};
const maxTrailPts = 60; 

for (const b of bodies) {
  pathVisible[b.id] = true;

  if (b.orbitPts.length >= 6) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(b.orbitPts, 3));
    const mat = new THREE.LineBasicMaterial({ color: new THREE.Color(b.color), transparent: true, opacity: 0.35 });
    const line = new THREE.Line(geo, mat);
    line.userData.isOrbitPath = true;
    line.userData.name = b.name;
    scene.add(line);
    staticLines[b.id] = line;
    
    const trailGeo = line.geometry.clone();
    const trailMat = new THREE.LineBasicMaterial({ color: new THREE.Color(b.color), transparent: true, opacity: 1.0, linewidth: 2 });
    const trailLine = new THREE.Line(trailGeo, trailMat);
    trailLine.geometry.setDrawRange(0, 0); 
    scene.add(trailLine);
    trailLines[b.id] = trailLine;
    orbitIndices[b.id] = 0; 
  }

const segs = b.id === 0 ? 24 : 16;

  const baseScale = DATA.earthOrbitUnits * 0.015;
  
  const visibilityScale = (b.id === 4) ? 0.25 : 1.0; 
  const minSafeRadius = baseScale * visibilityScale;
  
  let finalRenderRadius = Math.max(b.radius, minSafeRadius)*0.1;
  if (b.id === 0) finalRenderRadius *= 5.0;
  
  const geo = new THREE.SphereGeometry(finalRenderRadius, segs, segs);
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(b.color), roughness: 0.85, metalness: 0.05 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.userData.bodyId = b.id;
  mesh.userData.name = b.name;
  scene.add(mesh);
  meshes[b.id] = mesh;

  const hitGeo = new THREE.SphereGeometry(finalRenderRadius * 15.0, 8, 8);
  const hitMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.0, depthWrite: false });
  const hitMesh = new THREE.Mesh(hitGeo, hitMat);
  hitMesh.userData.bodyId = b.id;
  scene.add(hitMesh);
  hitMeshes[b.id] = hitMesh;

  const div = document.createElement('div');
  div.textContent = b.name;
  div.style.cssText = 'position:absolute;color:#c7cbd1;font-size:10px;font-family:inherit;transform:translate(8px,-6px);white-space:nowrap;text-shadow:0 0 4px #000,0 0 4px #000;';
  labelLayer.appendChild(div);
  labelDiv[b.id] = div;
}

const legendEl = document.getElementById('legend');
for (const b of bodies) {
  const item = document.createElement('div');
  item.className = 'item';
  item.innerHTML = `
    <span class="sw" style="background:${b.color}"></span>
    <span class="name">${b.name}</span>
  `;
  
  item.querySelector('.sw').onclick = function() {
    const isVisible = !pathVisible[b.id];
    pathVisible[b.id] = isVisible;
    if (staticLines[b.id]) staticLines[b.id].visible = isVisible;
    if (trailLines[b.id]) trailLines[b.id].visible = isVisible;
    item.style.opacity = isVisible ? "1.0" : "0.35";
  };

  item.querySelector('.name').onclick = function() {
    followId = b.id;
    meshes[followId].getWorldPosition(tmpV);
    controls.target.copy(tmpV);
    controls.update();
  };
  
  legendEl.appendChild(item);
}

document.getElementById('hudBodies').textContent = bodies.length;
if (DATA.earthOrbitUnits) {
    document.getElementById('hudScale').innerHTML = `1 Base Unit &asymp; ${DATA.earthOrbitUnits.toFixed(1)}u`;
}

const hoverRaycaster = new THREE.Raycaster();
hoverRaycaster.params.Line.threshold = DATA.earthOrbitUnits * 0.02; 
const mouseVector = new THREE.Vector2();

const tooltip = document.createElement('div');
tooltip.style.cssText = 'position:fixed;background:rgba(4,6,9,0.92);border:1px solid #ffb300;padding:6px 10px;font-size:11px;color:#fff;pointer-events:none;display:none;z-index:100;backdrop-filter:blur(4px);font-family:inherit;text-transform:uppercase;letter-spacing:0.05em;';
document.body.appendChild(tooltip);

window.addEventListener('pointermove', (e) => {
  mouseVector.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouseVector.y = -(e.clientY / window.innerHeight) * 2 + 1;
  
  hoverRaycaster.setFromCamera(mouseVector, camera);
  const activePaths = scene.children.filter(obj => obj.isLine && obj.userData.isOrbitPath && obj.visible);
  const intersections = hoverRaycaster.intersectObjects(activePaths);
  
  if (intersections.length > 0) {
    tooltip.style.display = 'block';
    tooltip.style.left = (e.clientX + 15) + 'px';
    tooltip.style.top = (e.clientY + 15) + 'px';
    tooltip.style.borderColor = '#' + intersections[0].object.material.color.getHexString();
    tooltip.innerHTML = `<span style="color:#777d84">Orbit Path:</span> ${intersections[0].object.userData.name}`;
  } else {
    tooltip.style.display = 'none';
  }
});

const raycaster = new THREE.Raycaster();
const mouseClickNDC = new THREE.Vector2();
let downPos = null;

renderer.domElement.addEventListener('pointerdown', (e) => { downPos = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downPos) return;
  const moved = Math.hypot(e.clientX - downPos[0], e.clientY - downPos[1]);
  downPos = null;
  if (moved > 4) return; 

  mouseVector.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouseVector.y = -(e.clientY / window.innerHeight) * 2 + 1;
  hoverRaycaster.setFromCamera(mouseVector, camera);
  
  const activePaths = scene.children.filter(obj => obj.isLine && obj.userData.isOrbitPath && obj.visible);
  const hits = hoverRaycaster.intersectObjects(activePaths);
  
  if (hits.length > 0) {
    const targetName = hits[0].object.userData.name;
    const body = bodies.find(b => b.name === targetName);
    if (body) {
        followId = body.id;
        meshes[followId].getWorldPosition(tmpV);
        controls.target.copy(tmpV);
        const bodyRadius = meshes[followId].geometry.parameters.radius;
        const zoomDist = Math.max(bodyRadius * 15, DATA.earthOrbitUnits * 0.5);
        const cameraOffset = new THREE.Vector3(1, 0.5, 1).normalize().multiplyScalar(zoomDist);
        camera.position.copy(tmpV).add(cameraOffset);
    }
  } else {
    followId = null;
  }
});

function fitView(animate = true) {
  const R = DATA.majorPlanetLimit * 1.15;
  const target = new THREE.Vector3(0, 0, 0);
  const dir = new THREE.Vector3(0.5, 0.65, 1).normalize();
  const dest = dir.multiplyScalar(R * 1.4);
  
  if (!animate) {
    camera.position.copy(dest);
    controls.target.copy(target);
    return;
  }
  const startPos = camera.position.clone();
  const startTarget = controls.target.clone();
  const t0 = performance.now();
  const dur = 1000;
  
  function step(now) {
    const t = Math.min(1, (now - t0) / dur);
    const e = t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2) / 2;
    camera.position.lerpVectors(startPos, dest, e);
    controls.target.lerpVectors(startTarget, target, e);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
fitView(false);

const timeline = document.getElementById('timeline');
timeline.max = String(nFrames - 1);
const stepTotalEl = document.getElementById('stepTotal');
const stepNowEl = document.getElementById('stepNow');
const yearNowEl = document.getElementById('yearNow');
stepTotalEl.textContent = stepsArr[stepsArr.length - 1] ?? (nFrames - 1);

let playing = true;  
let frameFloat = 0;
const SPEEDS = [0.25, 1, 4, 16, 64];
let speedIdx = 1;

const speedGroup = document.getElementById('speedGroup');
SPEEDS.forEach((s, i) => {
  const b = document.createElement('button');
  b.className = 'ctl' + (i === speedIdx ? ' active' : '');
  b.textContent = s + 'x';
  b.onclick = () => {
    speedIdx = i;
    [...speedGroup.children].forEach((c, j) => c.classList.toggle('active', j === i));
  };
  speedGroup.appendChild(b);
});

const playBtn = document.getElementById('playBtn');
playBtn.innerHTML = '&#10074;&#10074; Pause'; 

playBtn.onclick = () => togglePlay();
function togglePlay() {
  playing = !playing;
  playBtn.innerHTML = playing ? '&#10074;&#10074; Pause' : '&#9654; Play';
}

window.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  if (e.code === 'Escape') { followId = null; } 
});
document.getElementById('fitBtn').onclick = () => { followId = null; fitView(true); };

timeline.addEventListener('input', () => {
  frameFloat = parseFloat(timeline.value);
  playing = false;
  playBtn.innerHTML = '&#9654; Play';
});

const posA = new THREE.Vector3(), posB = new THREE.Vector3(), posOut = new THREE.Vector3();

function setFrame(f) {
  const f0 = Math.floor(f);
  const f1 = Math.min(nFrames - 1, f0 + 1);
  const frac = f - f0;
  
  for (const b of bodies) {
    const bi = bodyOrder.indexOf(b.id);
    if (bi < 0) continue;
    
    framePos(f0, bi, posA);
    framePos(f1, bi, posB);
    posOut.lerpVectors(posA, posB, frac);
    
    if (pathVisible[b.id] && trailLines[b.id] && b.orbitPts.length > 0) {
      const pts = b.orbitPts;
      const numPts = pts.length / 3;
      let bestIdx = orbitIndices[b.id] || 0;
      let minDist = Infinity;
      
      const searchRadius = 1500; 
      for (let offset = -searchRadius; offset <= searchRadius; offset++) {
        let i = bestIdx + offset;
        if (i < 0 || i >= numPts) continue; 
        
        const idx3 = i * 3;
        const dx = pts[idx3] - posOut.x;
        const dy = pts[idx3+1] - posOut.y;
        const dz = pts[idx3+2] - posOut.z;
        const distSq = dx*dx + dy*dy + dz*dz;
        
        if (distSq < minDist) {
          minDist = distSq;
          bestIdx = i;
        }
      }
      
      orbitIndices[b.id] = bestIdx;

      const trailLength = 250; 
      const drawStart = Math.max(0, bestIdx - trailLength);
      const drawCount = bestIdx - drawStart + 1;
      
      trailLines[b.id].geometry.setDrawRange(drawStart, drawCount);
    }

    meshes[b.id].position.copy(posOut);
    if (b.id === 0) sunLight.position.copy(posOut);

    const screen = posOut.clone().project(camera);
    const visible = screen.z < 1;
    const x = (screen.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-screen.y * 0.5 + 0.5) * window.innerHeight;
    labelDiv[b.id].style.display = visible ? 'block' : 'none';
    labelDiv[b.id].style.left = x + 'px';
    labelDiv[b.id].style.top = y + 'px';
  }
  
  timeline.value = String(f0);
  
  const currentStep = stepsArr[f0] ?? f0;
  stepNowEl.textContent = currentStep;
  yearNowEl.textContent = (2000 + currentStep / 365.25).toFixed(2);
}

function animate() {
  requestAnimationFrame(animate);

  if (playing) {
    frameFloat += SPEEDS[speedIdx] * 0.25;
    if (frameFloat >= nFrames - 1) frameFloat = 0;
  }
  
  setFrame(frameFloat);

  if (followId !== null && meshes[followId]) {
    controls.enableDamping = false;

    const targetMesh = meshes[followId];
    const oldTarget = controls.target.clone();
    
    targetMesh.getWorldPosition(tmpV);
    controls.target.copy(tmpV);
    
    const deltaMovement = tmpV.clone().sub(oldTarget);
    camera.position.add(deltaMovement);
  } else {
    controls.enableDamping = true;
  }

  controls.update();
  renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

document.getElementById('loading').style.display = 'none';
animate();
</script>
</body>
</html>
"""

html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
with open(OUT_PATH, "w") as f:
    f.write(html)

print(f"Wrote {OUT_PATH} ({len(html)/1e6:.2f} MB). Open it directly in a browser.")
