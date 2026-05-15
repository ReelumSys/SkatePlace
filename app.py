import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
import json
import os
import math
import requests
from dotenv import load_dotenv
from supabase_utils import supabase, sign_in, sign_up, update_my_location, get_all_live_locations

load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

st.set_page_config(page_title="SkatePlace GIS", layout="wide")

# --- Session State Initialisierung ---
if "user" not in st.session_state:
    st.session_state.user = None
if "live_mode" not in st.session_state:
    st.session_state.live_mode = False

# --- CUSTOM CSS THEME (Urban Night Rider) ---
st.markdown(\"\"\"\
    <style>\
    .stApp {\
        background-color: #000000;\
        color: #FFFFFF;\
    }\
    [data-testid=\"stSidebar\"] {\
        background-color: #0a0a0a !important;\
        border-right: 2px solid #00f2ff;\
    }\
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {\
        color: #00f2ff !important;\
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\
        text-transform: uppercase;\
        letter-spacing: 2px;\
    }\
    .stButton > button {\
        background-color: #00f2ff !important;\
        color: #000000 !important;\
        font-weight: bold !important;\
        border-radius: 5px !important;\
        border: none !important;\
        transition: all 0.3s ease !important;\n    }\
    .stButton > button:hover {\
        background-color: #ffffff !important;\
        color: #000000 !important;\
        transform: scale(1.05);\n    }\
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > input {\
        background-color: #1a1a1a !important;\
        color: #00f2ff !important;\
        border: 1px solid #333 !important;\
        border-radius: 8px !important;\n    }\
    div[data-testid=\"stVerticalBlock\"] > div:has(div.stMarkdown h3) {\
        background-color: #111 !important;\
        padding: 15px !important;\
        border-radius: 15px !important;\
        border: 1px solid #222 !important;\
        box-shadow: 0px 4px 15px rgba(0, 242, 255, 0.1) !important;\n    }\
    label, .stMarkdown p {\
        color: #ccc !important;\n    }\
    </style>\
    \"\", unsafe_allow_html=True)

# --- DATENBANK-LOGIK (Local JSON File) ---
DB_FILE = \"spots_db.json\"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, \"r\", encoding=\"utf-8\") as f:
                return json.load(f)
        except Exception as e:
            st.error(f\"Fehler beim Laden der DB: {e}\")
            return []
    return []

def save_data(spots):
    try:
        with open(DB_FILE, \"w\", encoding=\"utf-8\") as f:
            json.dump(spots, f, indent=4)
    except Exception as e:
        st.error(f\"Fehler beim Speichern der DB: {e}\")

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_weather(lat, lon):
    if not WEATHER_API_KEY:
        return None
    try:
        url = f\"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=de\"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                \"temp\": data[\"main\"][\"temp\"],
                \"desc\": data[\"weather\"][0][\"description\"],
                \"icon\": data[\"weather\"][0][\"icon\"],
                \"humidity\": data[\"main\"][\"humidity\"]\n            }
    except Exception as e:
        print(f\"Weather Error: {e}\")
    return None

if 'spots' not in st.session_state:
    st.session_state.spots = load_data()

# --- SIDEBAR: AUTH & ACCOUNT ---
with st.sidebar:
    st.title(\"🛹 SkatePlace Hub\")
    if st.session_state.user is None:
        st.subheader(\"Login / Register\")
        choice = st.radio(\"Wähle eine Aktion:\", [\"Login\", \"Register\"])
        email = st.text_input(\"Email\")
        password = st.text_input(\"Passwort\", type=\"password\")
        if choice == \"Register\":
            username = st.text_input(\"Username\")
            if st.button(\"Account erstellen\"):
                user, err = sign_up(email, password, username)
                if err: st.error(err)
                else: st.success(\"Account erstellt! Bitte einloggen.\")
        if st.button(\"Einloggen\"):
            user, err = sign_in(email, password)
            if err: st.error(err)
            else: 
                st.session_state.user = user.user
                st.rerun()
    else:
        st.subheader(f\"Hi, {st.session_state.user.email}!\")
        st.session_state.live_mode = st.toggle(\"Sichtbar für die Crew 📡\", value=st.session_state.live_mode)
        if st.button(\"Logout\"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.live_mode = False
            st.rerun()

    st.markdown(\"---\\n\")
    st.header(\"🗺️ Karten-Einstellungen\")
    center_lat = st.sidebar.number_input(\"Zentrum Breitengrad\", value=52.369) if 'center_lat' not in locals() else center_lat
    # Fixed the local scope issue for sidebar inputs
    center_lat = st.sidebar.number_input(\"Zentrum Breitengrad\", value=52.369)
    center_lon = st.sidebar.number_input(\"Zentrum Längengrad\", value=9.931)
    zoom = st.sidebar.slider(\"Zoom\", 1, 20, 12)

    st.sidebar.markdown(\"---\\n\")
    st.sidebar.subheader(\"🔍 Suche & Filter\")
    search_query = st.sidebar.text_input(\"Spots suchen...\", placeholder=\"Name oder Tag (z.B. gap)...\").lower()

    st.sidebar.markdown(\"---\")
    st.sidebar.markdown(\"**Spot Filter**\")
    all_types = [\"Ledge\", \"Rail\", \"Bowl\", \"Manual Pad\", \"Stairs\", \"Wallride\", \"Andere\"]
    selected_types = st.sidebar.multiselect(\"Spot Typ\", options=all_types, default=all_types)
    all_diffs = [\"Easy\", \"Medium\", \"Hard\", \"Pro\"]
    selected_diffs = st.sidebar.multiselect(\"Schwierigkeit\", options=all_diffs, default=all_diffs)
    all_surfaces = [\"Beton\", \"Marmor\", \"Asphalt\", \"Holz\", \"Fliesen\", \"Andere\"]
    selected_surfaces = st.sidebar.multiselect(\"Bodenbelag\", options=all_surfaces, default=all_surfaces)

    st.sidebar.markdown(\"---\")
    st.sidebar.subheader(\"🔥 Layer & Sichtbarkeit\")
    show_heatmap = st.sidebar.checkbox(\"Heatmap anzeigen\", value=False)
    show_markers = st.sidebar.checkbox(\"Spots anzeigen\", value=True)

    st.sidebar.markdown(\"---\")
    st.sidebar.subheader(\"📏 Distanz-Check\")
    user_lat = st.sidebar.number_input(\"Dein Breitengrad\", value=center_lat)
    user_lon = st.sidebar.number_input(\"Dein Längengrad\", value=center_lon)
    max_dist = st.sidebar.slider(\"Radius (km)\", 1, 50, 10)

# Update Live Location
if st.session_state.user and st.session_state.live_mode:
    update_my_location(st.session_state.user.id, st.session_state.user.email, user_lat, user_lon)
elif st.session_state.user:
    update_my_location(st.session_state.user.id, st.session_state.user.email, 0.0, 0.0, status=\"offline\")

st.title(\"🛹 SkatePlace - Live Edition\")
st.markdown(\"Live Tracking integriert. Melde dich ein, um deine Crew zu sehen!\")

# Filter Logic
filtered_spots = st.session_state.spots
if search_query:
    keywords = search_query.split()
    filtered_spots = [spot for spot in filtered_spots if all(kw in spot.get('name', '').lower() or any(kw in tag.lower() for tag in spot.get('tags', [])) for kw in keywords)]
filtered_spots = [spot for spot in filtered_spots if spot.get('type') in selected_types and spot.get('diff') in selected_diffs and spot.get('surface') in selected_surfaces]

# Map creation
def create_map(lat, lon, zoom_level, spots, show_heatmap, show_markers):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_level, tiles='CartoDB dark_matter', attr='&copy; OpenStreetMap contributors &copy; CARTO')
    if show_heatmap and spots:
        HeatMap([[spot['lat'], spot['lon']] for spot in spots]).add_to(m)
    if show_markers:
        marker_cluster = MarkerCluster().add_to(m)
        type_icons = {\"Ledge\": \"building\", \"Rail\": \"road\", \"Bowl\": \"water\", \"Manual Pad\": \"home\", \"Stairs\": \"stairs\", \"Wallride\": \"mountain\", \"Andere\": \"info-sign\"}
        for spot in spots:
            diff = spot.get('diff', 'Medium')
            color = \"green\" if diff == \"Easy\" else \"orange\" if diff == \"Medium\" else \"red\"
            folium.Marker(location=[spot['lat'], spot['lon']], popup=f\"<b>{spot.get('name', 'Unbenannt')}</b>\", tooltip=spot.get('name', 'Spot'), icon=folium.Icon(color=color, icon=type_icons.get(spot.get('type', 'Andere'), 'info-sign'))).add_to(marker_cluster)
    
    # LIVE USERS LAYER
    live_users = get_all_live_locations()
    for user in live_users:
        if st.session_state.user and user['user_id'] == st.session_state.user.id:
            continue
        folium.Marker([user['latitude'], user['longitude']], popup=f\"Crew: {user['username']}\", tooltip=user['username'], icon=folium.Icon(color='blue', icon='bicycle', prefix='fa')).add_to(m)
        
    return m

map_obj = create_map(center_lat, center_lon, zoom, filtered_spots, show_heatmap, show_markers)
output = st_folium(map_obj, width=1200, height=600)

# --- The rest of the Spot management (matching original app.py) ---
if output.get(\"last_clicked\"):
    clicked_coords = output[\"last_clicked\"]
    lat, lon = clicked_coords[\"lat\"], clicked_coords[\"lng\"]
    st.sidebar.info(f\"Koordinaten: `{lat:.5f}, {lon:.5f}`\")
    with st.sidebar:
        spot_name = st.text_input(\"Name des Spots\")
        spot_type = st.selectbox(\"Art des Spots\", all_types)
        spot_diff = st.select_slider(\"Schwierigkeit\", options=all_diffs)
        spot_surface = st.selectbox(\"Bodenbelag\", all_surfaces)
        spot_status = st.checkbox(\"Aktuell skatebar?\", value=True)
        spot_tags = st.text_input(\"Tags (mit Komma trennen)\")
        spot_clip = st.text_input(\"Clip URL\")
        spot_crowd = st.select_slider(\"Crowd-Level\", options=[\"Leer\", \"Chillig\", \"Normal\", \"Überlaufen\"])
        uploaded_file = st.file_uploader(\"Foto hochladen\", type=[\"jpg\", \"jpeg\", \"png\"])
        if st.button(\"Spot speichern 💾\"):
            if spot_name:
                photo_filename = \"Kein Foto\"
                if uploaded_file:
                    import uuid
                    ext = os.path.splitext(uploaded_file.name)[1]
                    unique_filename = f\"{uuid.uuid4()}{ext}\"
                    with open(os.path.join(\"uploads\", unique_filename), \"wb\") as f: f.write(uploaded_file.getbuffer())
                    photo_filename = unique_filename
                new_spot = {\"lat\": lat, \"lon\": lon, \"name\": spot_name, \"type\": spot_type, \"diff\": spot_diff, \"surface\": spot_surface, \"status\": \"Skatebar\" if spot_status else \"Gesperrt\", \"tags\": [t.strip() for t in spot_tags.split(\",\")] if spot_tags else [], \"clip\": spot_clip, \"crowd\": spot_crowd, \"likes\": 0, \"photo\": photo_filename}
                st.session_state.spots.append(new_spot)
                save_data(st.session_state.spots)
                st.success(f\"Spot '{spot_name}' gespeichert!\")
                st.rerun()
            else: st.error(\"Bitte gib einen Namen ein!\")

if st.session_state.spots:
    st.write(\"### 📏 Nächste Spots in deiner Nähe\")
    spots_with_dist = sorted([(calculate_distance(user_lat, user_lon, s['lat'], s['lon']), s) for s in filtered_spots if calculate_distance(user_lat, user_lon, s['lat'], s['lon']) <= max_dist], key=lambda x: x[0])
    if spots_with_dist:
        nearby_cols = st.columns(3)
        for i, (dist, spot) in enumerate(spots_with_dist):
            with nearby_cols[i % 3]: st.info(f\"**{spot.get('name', 'Unbenannt')}** — {dist:.2f} km entfernt\")
    else: st.write(\"Keine Spots gefunden. 🤷‍♂️\")
    
    st.write(\"### 📍 Deine Skate-Spot Liste\")
    if not filtered_spots: st.warning(\"Keine Spots gefunden!\")
    else:
        spot_to_view = st.selectbox(\"Wähle einen Spot:\", options=filtered_spots, format_func=lambda x: x.get('name', 'Unbenannt'))
        if spot_to_view:
            st.markdown(\"---\")
            col_img, col_info = st.columns([1, 1])
            with col_img:
                if spot_to_view.get('photo') != \"Kein Foto\":
                    img_path = os.path.join(\"uploads\", spot_to_view.get('photo'))
                    if os.path.exists(img_path): st.image(img_path, use_column_width=True)
                    else: st.write(\"🖼️ Bild nicht gefunden\")
                else: st.write(\"❌ Kein Foto available\")
                if spot_to_view.get('clip'): st.markdown(f\"[Watch Clip]({spot_to_view['clip']})\")
            with col_info:
                st.subheader(f\"🛹 {spot_to_view.get('name', 'Unbenannt')}\")
                weather = get_weather(spot_to_view['lat'], spot_to_view['lon'])
                if weather:
                    st.markdown(f\"<div style='background-color: #1a1a1a; padding: 10px; border-radius: 10px; border-left: 5px solid #00f2ff;'>☁️ <b>{weather['temp']}°C</b> | {weather['desc']}</div>\", unsafe_allow_html=True)
                st.write(f\"**Typ:** {spot_to_view.get('type')} | **Diff:** {spot_to_view.get('diff')}\")
                st.write(f\"**Boden:** {spot_to_view.get('surface')} | **Status:** {spot_to_view.get('status')}\")
                st.write(f\"**Crowd:** {spot_to_view.get('crowd')}\")
                google_maps_url = f\"https://www.google.com/maps/search/?api=1&query={spot_to_view['lat']},{spot_to_view['lon']}\"
                st.markdown(f\"[📍 Google Maps]({google_maps_url})\")
                likes = spot_to_view.get('likes', 0)
                if st.button(f\"❤️ {likes} Likes\", key=f\"like_{id(spot_to_view)}\"):
                    spot_to_view['likes'] = likes + 1
                    save_data(st.session_state.spots)
                    st.rerun()
            st.markdown(\"---\")
        st.write(\"### 📍 All Spots Overview\")
        cols = st.columns(3)
        for i, spot in enumerate(filtered_spots):
            with cols[i % 3]:
                st.markdown(\"---\")
                st.subheader(f\"🛹 {spot.get('name', 'Unbenannt')}\")
                st.write(f\"**Typ:** {spot.get('type')} | **Diff:** {spot.get('diff')}\")
                if st.button(f\"Spot löschen\", key=f\"del_{id(spot)}\"):
                    st.session_state.spots.remove(spot)
                    save_data(st.session_state.spots)
                    st.rerun()
