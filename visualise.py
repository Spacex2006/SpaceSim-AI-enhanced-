import pandas as pd
import plotly.graph_objects as go

# Body names and colors matching solar_system.json order
names = [
    "Sun", "Mercury", "Venus", "Earth", "Moon", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Halley",
    "Ceres", "Eris", "Makemake", "Haumea", "Sedna",
    "Hale-Bopp", "Encke"
]

colors = [
    "yellow", "gray", "orange", "deepskyblue", "silver", "red",
    "peru", "gold", "cyan", "royalblue", "white", "lime",
    "lightblue", "violet", "pink", "salmon", "darkorange",
    "aquamarine", "chartreuse"
]

# Read simulation output
df = pd.read_csv("data/simulation_output.csv")

fig = go.Figure()

for body_id in df["body_id"].unique():
    body_data = df[df["body_id"] == body_id]
    name  = names[body_id]
    color = colors[body_id]

    # Draw the orbital path
    fig.add_trace(go.Scatter(
        x=body_data["x"],
        y=body_data["y"],
        mode="lines",
        name=name,
        line=dict(color=color, width=1),
        hovertemplate=f"<b>{name}</b><br>x: %{{x:.3e}} km<br>y: %{{y:.3e}} km<extra></extra>"
    ))

    # Draw a dot at the final position
    fig.add_trace(go.Scatter(
        x=[body_data["x"].iloc[-1]],
        y=[body_data["y"].iloc[-1]],
        mode="markers",
        name=f"{name} (final)",
        marker=dict(color=color, size=8),
        showlegend=False,
        hovertemplate=f"<b>{name}</b><br>x: %{{x:.3e}} km<br>y: %{{y:.3e}} km<extra></extra>"
    ))

fig.update_layout(
    title="Solar System Simulation",
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white"),
    xaxis=dict(
        title="X position (km)",
        gridcolor="#222222",
        zerolinecolor="#444444",
        scaleanchor="y",   # Keep aspect ratio equal
        scaleratio=1,
    ),
    yaxis=dict(
        title="Y position (km)",
        gridcolor="#222222",
        zerolinecolor="#444444",
    ),
    legend=dict(
        bgcolor="black",
        bordercolor="#444444",
        borderwidth=1,
    ),
    hovermode="closest",
)

# Save as interactive HTML file and open in browser
fig.write_html("data/orbits.html")
fig.show()