import streamlit as st
import pandas as pd
import folium
from geopy.distance import distance
import numpy as np
from streamlit_folium import st_folium
import csv
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union

# --------------------------------------
# Config: raw CSV URL from your GitHub repo
# --------------------------------------
CSV_URL = "https://raw.githubusercontent.com/thao-nguyen-10/hub-coverage/main/csv_network_lat_lon_final_v3.csv"

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
def create_map(df, wards_df, radius_km, city_name):
    city_centers = {
        "Hà Nội": [21.0285, 105.8542],
        "TP. Hồ Chí Minh": [10.7769, 106.7009]
    }

    # Choose projection based on city
    if city_name == "Hà Nội":
        epsg_code = 3405  # VN-2000 / Hanoi
    else:
        epsg_code = 3406  # VN-2000 / HCM

    # Create GeoDataFrame from input DataFrame
    geometry_all = [Point(lon, lat) for lon, lat in zip(df['lon'], df['lat'])]
    geometry_filtered = [Point(lon, lat) for lon, lat in zip(filtered_df['lon'], df['lat'])]
    
    gdf_all = gpd.GeoDataFrame(df, geometry=geometry_all, crs="EPSG:4326").to_crs(epsg=epsg_code)
    gdf_filtered = gpd.GeoDataFrame(filtered_df, geometry=geometry_filtered, crs="EPSG:4326").to_crs(epsg=epsg_code)
    
    # Project to meters for buffering
    buffers = gdf_filtered.buffer(radius_km * 1000)
    buffer_union = unary_union(buffers)
    # gdf_m = gdf.to_crs(epsg=3857)

    # Check which full-wards are inside the buffer area
    gdf_all["within_buffer"] = gdf_all.geometry.within(buffer_union)
    wards_within = gdf_all[gdf_all["within_buffer"]]

    # Coverage Calculations
    ward_coverage = len(wards_within)
    all_wards = len(gdf_all)
    
    sale_coverage = wards_within["sale"].sum() / gdf_all["sale"].sum() * 100

    # Load city boundary polygon (replace with real Hanoi/HCM boundaries!)
    if city_name == "Hà Nội":
        city_poly = gpd.read_file("https://raw.githubusercontent.com/thao-nguyen-10/hub-coverage/refs/heads/main/hn.geojson").to_crs(epsg=3405)
    else:
        city_poly = gpd.read_file("https://raw.githubusercontent.com/thao-nguyen-10/hub-coverage/refs/heads/main/hcm.geojson").to_crs(epsg=3406)

    city_poly = city_poly[city_poly.is_valid].explode(index_parts=False)
    
    map_center = city_centers.get(city_name, [16.0, 108.0])
    m = folium.Map(location=map_center, zoom_start=12)

    for _, row in wards_df.iterrows():
        # folium.Circle(
        #     location=(row.lat, row.lon),
        #     radius=radius_km * 1000,
        #     color='blue',
        #     fill=True,
        #     fill_opacity=0.25,
        #     popup=row['ward']
        # ).add_to(m)
        
        lat, lon = row["lat"], row["lon"]
        name = row["ward"]
        district = row["district"]
        ranking = row["final_ranking"]

        # folium.Marker(
        #     location=[lat, lon],
        #     popup=f"{name}, {district}, Rank: {ranking}",
        #     icon=folium.Icon(color="blue")
        # ).add_to(m)

        polygon_points = geodesic_circle(lat, lon, radius_km)
        folium.Polygon(
            locations=polygon_points,
            color="blue",
            fill=True,
            fill_opacity=0.15,
            weight=1
        ).add_to(m)

        # Add city boundary outline
        city_poly_wgs84 = city_poly.to_crs(epsg=4326)
        folium.GeoJson(
            data=city_poly_wgs84.__geo_interface__,
            style_function=lambda x: {"color": "red", "fill": False, "weight": 2},
            name="City Boundary"
        ).add_to(m)

    return m, ward_coverage, all_wards, sale_coverage

# --------------------------------------
# Streamlit UI
# --------------------------------------
st.title("🗺️ Ward Coverage Map (Ha Noi & HCM City)")

# Load data from GitHub
try:
    df = pd.read_csv(CSV_URL, quoting=csv.QUOTE_NONE, encoding='utf-8')
    st.success("✅ Loaded ward data from GitHub")
except Exception as e:
    st.error(f"❌ Failed to load CSV: {e}")
    st.stop()

# Input controls
city = st.selectbox("Select City", options=["Hà Nội", "TP. Hồ Chí Minh"])
n_nodes = st.number_input("Number of nodes to display", min_value=1, max_value=1000, value=30)
radius_km = st.number_input("Distance radius (km)", min_value=0.1, max_value=50.0, value=2.0)

# Filter data
df_city = df[df["city"] == city]
filtered_df = df[df["city"] == city].sort_values(by="final_ranking").head(n_nodes)

if filtered_df.empty:
    st.warning("No data available for the selected city.")
else:
    # Create and display map
    ward_map, ward_coverage, all_wards, sale_coverage = create_map(df_city, filtered_df, radius_km, city)
    
    # district_df = df[(df["city"] == city) & (df["district"].isin(districts))]
    # sale_coverage = district_df["sale"].sum() / df[df["city"] == city]["sale"].sum()
    # sale_coverage = sale_coverage * 100

    district_coverage = filtered_df["district"].nunique()
    all_districts = df[df["city"] == city]["district"].nunique()
    
    st.metric("Coverage Sale (%)", f"{sale_coverage:.2f}%")
    st.metric("District Coverage ", f"{district_coverage} out of {all_districts} districts")
    st.metric("Ward Coverage ", f"{ward_coverage} out of {all_wards} wards")
    st_folium(ward_map, width=700, height=500)
    st.subheader("Top Selected Wards")
    st.dataframe(filtered_df)
