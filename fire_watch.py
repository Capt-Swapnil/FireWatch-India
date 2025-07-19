import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta, time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic 
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderRateLimited
import time

NASA_FIRMS_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/country/csv/viirs"
)
def get_fire_data():
    url = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv/' + '68be5f1e11a8b3a2bda31093ae7278fc' + '/VIIRS_NOAA20_NRT/68,6,97,37/3'
    try:
        df = pd.read_csv(url)
        return df
    except:
        st.warning("Failed to fetch FIRMS data.")
        return pd.DataFrame()

st.set_page_config(page_title="🔥 Fire Detection System", layout="wide")
st.markdown(
    "<h1 style='text-align: center; color: red;'>🔥 Real-Time Fire Detection Across India</h1>", 
    unsafe_allow_html=True
)
st.markdown("---")

with st.sidebar:
    st.markdown("### 🌍 Enter Your Location")
    district = st.text_input("District / County")
    city = st.text_input("City")
    state = st.text_input("State / Region")
    country = st.text_input("Country", "India")


    show_map = st.checkbox("Show map of fires", value=True)


def geocode_location(district, city, state, country):
    geolocator = Nominatim(user_agent="fire-detector", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=3)
    full_address = ", ".join(filter(None, [district, city, state, country]))
    
    retries = 3
    for attempt in range(retries):
        try:
            location = geolocator.geocode(full_address)
            if location:
                return location.latitude, location.longitude
            else:
                return None, None
        except GeocoderRateLimited as e:
            wait_time = 2 ** attempt  
            print(f"Rate limit exceeded, retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # If all retries fail
    print("Geocoding failed due to rate limits.")
    return None, None



def filter_nearby_fires(df, user_lat, user_lon, radius_km=50):
    filtered = []
    for _, row in df.iterrows():
        try:
            lat, lon = float(row['latitude']), float(row['longitude'])
            dist = geodesic((user_lat, user_lon), (lat, lon)).kilometers
            if dist <= radius_km:
                row['distance_km'] = round(dist, 2)
                filtered.append(row)
        except:
            continue
    return pd.DataFrame(filtered)

if all([district, city, state, country]):
    user_lat, user_lon = geocode_location(district, city, state, country)
    fire_df = get_fire_data()

    if user_lat is not None and user_lon is not None:
        fire_df = filter_nearby_fires(fire_df, user_lat, user_lon, radius_km=50)

        if not fire_df.empty:
            st.success(f"🔥 Fetched {len(fire_df)} fire records near your location in the last 24 hours.")

            if show_map:
                st.subheader("🗺️ Fire Locations")
                if user_lat is not None and user_lon is not None:
                    m = folium.Map(location=[user_lat, user_lon], zoom_start=6)
                else:
                    st.warning("Please enter a valid location")

                locations = []

                for _, row in fire_df.iterrows():
                    try:
                        lat = float(row['latitude'])
                        lon = float(row['longitude'])

                        if not (pd.isna(lat) or pd.isna(lon)):
                            loc = [lat, lon]
                            locations.append(loc)

                            folium.CircleMarker(
                                location=loc,
                                radius=5,
                                color='red' if row.get('bright_ti4', 0) > 360 else 'orange',
                                fill=True,
                                fill_color='red' if row.get('bright_ti4', 0) > 360 else 'orange',  
                                fill_opacity=0.6,
                                tooltip=f"Brightness: {row.get('bright_ti4', 'N/A')}"
                            ).add_to(m)
                    except:
                        continue

                if locations:
                    m.fit_bounds(locations)

                st_data = st_folium(m, width=1200, height=600)
                st.subheader("🚨 Fire Severity Alert")
                severe_fires = fire_df[fire_df['bright_ti4'] > 360]
                if len(severe_fires) > 50:
                    st.error("🔴 Severe fire risk detected in the region! Be careful , kindly evacuate the place ASAP!")
                elif len(severe_fires) > 10:
                    st.warning("🟠 Moderate fire activity detected. There's low chance of fire but , call your nearest fire station!")
                else:
                    st.success("🟢 Low fire risk currently. It's safe to visit the place! ")

        else:
            st.info("✅ No fire data available for the selected region in the last 24 hours.")
    else:
        st.warning("⚠️ Could not locate the entered address. Please check your input.")
else:
    st.info("📍 Please enter your full location details in the sidebar to begin.")



