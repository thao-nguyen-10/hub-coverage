import streamlit as st
import pandas as pd
import folium
from geopy.distance import distance
import numpy as np
from streamlit_folium import st_folium

# --------------------------------------
# Config: raw CSV URL from your GitHub repo
# --------------------------------------
CSV_URL = "https://github.com/thao-nguyen-10/hub-coverage/blob/main/csv_network_lat_lon_final.csv"

# --------------------------------------
# Utility: Generate geodesic circle (polygon)
# --------------------------------------
def geodesic_circle(center_lat, center_lon, radius_km, num_points=60):
    angles = np.linspace(0, 360, num_points)
    circle_points = []
    for angle in angles:
        dest = distance(kilometers=radius_km).destination((center_lat, center_lon), bearing=angle)
        circle_points.append((dest.latitude, dest.longitude))
    return circle_points

# --------------------------------------
# Utility: Draw map with polygons
# --------------------------------------
def create_map(wards_df, radius_km, city_name):
    city_centers = {
        "Ha Noi": [21.0285, 105.8542],
        "Ho Chi Minh": [10.7769, 106.7009]
    }
    map_center = city_centers.get(city_name, [16.0, 108.0])
    m = folium.Map(location=map_center, zoom_start=12)

    for _, row in wards_df.iterrows():
        lat, lon = row["latitude"], row["longitude"]
        name = row["ward"]
        district = row["district"]
        ranking = row["ranking"]

        folium.Marker(
            location=[lat, lon],
            popup=f"{name}, {district}, Rank: {ranking}",
            icon=folium.Icon(color="blue")
        ).add_to(m)

        polygon_points = geodesic_circle(lat, lon, radius_km)
        folium.Polygon(
            locations=polygon_points,
            color="blue",
            fill=True,
            fill_opacity=0.15,
            weight=1
        ).add_to(m)

    return m

# --------------------------------------
# Streamlit UI
# --------------------------------------
st.title("🗺️ Ward Coverage Map (Ha Noi & HCM City)")

# Load data from GitHub
try:
    df = pd.read_csv(CSV_URL)
    st.success("✅ Loaded ward data from GitHub")
except Exception as e:
    st.error(f"❌ Failed to load CSV: {e}")
    st.stop()

# Input controls
city = st.selectbox("Select City", options=["Ha Noi", "Ho Chi Minh"])
n_nodes = st.number_input("Number of nodes to display", min_value=1, max_value=1000, value=30)
radius_km = st.number_input("Distance radius (km)", min_value=0.1, max_value=10.0, value=2.0)

# Filter data
filtered_df = df[df["city"] == city].sort_values(by="ranking").head(n_nodes)

if filtered_df.empty:
    st.warning("No data available for the selected city.")
else:
    # Create and display map
    ward_map = create_map(filtered_df, radius_km, city)
    st_folium(ward_map, width=700, height=500)
