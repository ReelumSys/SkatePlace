import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import json
import os
import math

st.set_page_config(page_title="SkatePlace GIS", layout="wide")

# --- CUSTOM CSS THEME (Urban Night Rider) ---
st.markdown("""
    <style>
    /* Global Background & Text */
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a !important;
        border-right: 2px solid #00f2ff;
    }
    
    /* Headers & Titles */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #00f2ff !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* Buttons Customization */
    .stButton > button {
        background-color: #00f2ff !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 5px !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background-color: #ffffff !important;
        color: #000000 !important;
        transform: scale(1.05);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > input {
        background-color: #1a1a1a !important;
        color: #00f2ff !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }
    
    /* Spot Cards Styling */
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown h3) {
        background-color: #111 !important;
        padding: 15px !important;
        border-radius: 15px !important;
        border: 1px solid #222 !important;
        box-shadow: 0px 4px 15px rgba(0, 242, 255, 0.1) !important;
    }
    
    /* Labels & Small Text */
    label, .stMarkdown p {
        color: #ccc !important;
    }
    </style>
    """, unsafe_allow_html=True)


# --- DATENBANK-LOGIK (Local JSON File) ---
DB_FILE = "spots_db.json"

def load_data():
    """Lädt die Spots aus der lokalen JSON-Datei."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Fehler beim Laden der DB: {e}")
            return []
    return []

def save_data(spots):
    """Speichert die aktuelle Spot-Liste in die lokale JSON-Datei."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(spots, f, indent=4)
    except Exception as e:
        st.error(f"Fehler beim Speichern der DB: {e}")

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates the distance between two points on Earth in km (Haversine formula)."""
    R = 6371 # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Initialisiere Session State mit Daten aus der Datei
if 'spots' not in st.session_state:
    st.session_state.spots = load_data()

st.title("🛹 SkatePlace - Classic Edition")
st.markdown("Zurück auf lokale JSON-Speicherung. Stabil und schnell. it Doppelklick Koordinaten auswählen.")

# Sidebar für Karten-Einstellungen
st.sidebar.header("🗺️ Karten-Einstellungen")
center_lat = st.sidebar.number_input("Zentrum Breitengrad", value=52.369)
center_lon = st.sidebar.number_input("Zentrum Längengrad", value=9.931)
zoom = st.sidebar.slider("Zoom", min_value=1, max_value=20, value=12)

st.sidebar.markdown("---\n")
st.sidebar.subheader("🔍 Suche & Filter")
search_query = st.sidebar.text_input("Spots suchen...", placeholder="Name oder Tag (z.B. gap)...").lower()

# --- Neue Interaktive Filter ---
st.sidebar.markdown("---")
st.sidebar.markdown("**Spot Filter**")

# Typ Filter (Multi-select)
all_types = ["Ledge", "Rail", "Bowl", "Manual Pad", "Stairs", "Wallride", "Andere"]
selected_types = st.sidebar.multiselect("Spot Typ", options=all_types, default=all_types)

# Schwierigkeit Filter (Multi-select)
all_diffs = ["Easy", "Medium", "Hard", "Pro"]
selected_diffs = st.sidebar.multiselect("Schwierigkeit", options=all_diffs, default=all_diffs)

# Bodenbelag Filter (Multi-select)
all_surfaces = ["Beton", "Marmor", "Asphalt", "Holz", "Fliesen", "Andere"]
selected_surfaces = st.sidebar.multiselect("Bodenbelag", options=all_surfaces, default=all_surfaces)

st.sidebar.markdown("---")
st.sidebar.subheader("🔥 Layer & Sichtbarkeit")
show_heatmap = st.sidebar.checkbox("Heatmap anzeigen", value=False)
show_markers = st.sidebar.checkbox("Spots anzeigen", value=True)

# --- Entfernungs-Check ---
st.sidebar.markdown("---")
st.sidebar.subheader("📏 Distanz-Check")
user_lat = st.sidebar.number_input("Dein Breitengrad", value=center_lat)
user_lon = st.sidebar.number_input("Dein Längengrad", value=center_lon)
max_dist = st.sidebar.slider("Radius (km)", 1, 50, 10)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Neuer Spot")

# Filter Spots based on search query and new filters
filtered_spots = st.session_state.spots

if search_query:
    filtered_spots = [
        spot for spot in filtered_spots 
        if search_query in spot.get('name', '').lower() or 
          any(search_query in tag.lower() for tag in spot.get('tags', []))
    ]

# Apply Type, Diff, and Surface filters
filtered_spots = [
    spot for spot in filtered_spots 
    if spot.get('type') in selected_types and 
       spot.get('diff') in selected_diffs and 
       spot.get('surface') in selected_surfaces
]

# Karte erstellen
def create_map(lat, lon, zoom_level, spots, show_heatmap, show_markers):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_level)
    
    if show_heatmap and spots:
        heat_data = [[spot['lat'], spot['lon']] for spot in spots]
        HeatMap(heat_data).add_to(m)
    
    if show_markers:
        for spot in spots:
            diff = spot.get('diff', 'Medium')
            color = "green" if diff == "Easy" else "orange" if diff == "Medium" else "red"
            popup_text = f"<b>{spot.get('name', 'Unbenannt')}</b><br>Typ: {spot.get('type', 'Unbekannt')}<br>Diff: {diff}"
            folium.Marker(
                location=[spot['lat'], spot['lon']],
                popup=popup_text,
                tooltip=spot.get('name', 'Spot'),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
    return m

map_obj = create_map(center_lat, center_lon, zoom, filtered_spots, show_heatmap, show_markers)
output = st_folium(map_obj, width=1200, height=600)

if output.get("last_clicked"):
    clicked_coords = output["last_clicked"]
    lat = clicked_coords["lat"]
    lon = clicked_coords["lng"]
    st.sidebar.info(f"Koordinaten: `{lat:.5f}, {lon:.5f}`")
    
    with st.sidebar:
        spot_name = st.text_input("Name des Spots", placeholder="z.B. Beton-Kante Mitte")
        spot_type = st.selectbox("Art des Spots", ["Ledge", "Rail", "Bowl", "Manual Pad", "Stairs", "Wallride", "Andere"])
        spot_diff = st.select_slider("Schwierigkeit", options=["Easy", "Medium", "Hard", "Pro"])
        spot_surface = st.selectbox("Bodenbelag", ["Beton", "Marmor", "Asphalt", "Holz", "Fliesen", "Andere"])
        spot_status = st.checkbox("Aktuell skatebar?", value=True)
        spot_tags = st.text_input("Tags (mit Komma trennen)", placeholder="z.B. gap, downhill, urban")
        spot_clip = st.text_input("Clip URL (Insta/YT)", placeholder="https://...")
        spot_crowd = st.select_slider("Crowd-Level", options=["Leer", "Chillig", "Normal", "Überlaufen"])
        uploaded_file = st.file_uploader("Foto hochladen", type=["jpg", "jpeg", "png"])
        
        if st.button("Spot speichern 💾"):
            if spot_name:
                # Handling the uploaded file and saving it locally
                photo_filename = "Kein Foto"
                if uploaded_file:
                    try:
                        import uuid
                        # Create a unique filename to avoid overwriting
                        ext = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{uuid.uuid4()}{ext}"
                        upload_path = os.path.join("uploads", unique_filename)
                        
                        with open(upload_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        photo_filename = unique_filename
                    except Exception as e:
                        st.error(f"Fehler beim Speichern des Bildes: {e}")

                new_spot = {
                    "lat": lat, 
                    "lon": lon, 
                    "name": spot_name,
                    "type": spot_type,
                    "diff": spot_diff,
                    "surface": spot_surface,
                    "status": "Skatebar" if spot_status else "Gesperrt",
                    "tags": [t.strip() for t in spot_tags.split(",")] if spot_tags else [],
                    "clip": spot_clip,
                    "crowd": spot_crowd,
                    "likes": 0,
                    "photo": photo_filename
                }
                st.session_state.spots.append(new_spot)
                save_data(st.session_state.spots)
                st.success(f"Spot '{spot_name}' lokal gespeichert!")
                st.rerun()
            else:
                st.error("Bitte gib einen Namen ein!")

if st.session_state.spots:
    st.write("### 📏 Nächste Spots in deiner Nähe")
    
    # Distanzen basierend auf GEFILTERTEN Spots berechnen
    spots_with_dist = []
    for spot in filtered_spots:
        dist = calculate_distance(user_lat, user_lon, spot['lat'], spot['lon'])
        if dist <= max_dist:
            spots_with_dist.append((dist, spot))
    
    spots_with_dist.sort(key=lambda x: x[0])
    
    if spots_with_dist:
        nearby_cols = st.columns(3)
        for i, (dist, spot) in enumerate(spots_with_dist):
            with nearby_cols[i % 3]:
                st.info(f"**{spot.get('name', 'Unbenannt')}** — {dist:.2f} km entfernt")
    else:
        st.write("Keine passenden Spots im gewählten Radius gefunden. 🤷‍♂️")

    st.write("---")
    st.write("### 📍 Deine Skate-Spot Liste")
    
    if not filtered_spots:
        st.warning("Keine Spots gefunden, die auf deine Suche passen!")
    else:
        cols = st.columns(3)
        for i, spot in enumerate(filtered_spots):
            with cols[i % 3]:
                # Wir brauchen den originalen Index für das Löschen/Liken
                original_index = st.session_state.spots.index(spot)
                st.markdown(f"---")
                st.subheader(f"🛹 {spot.get('name', 'Unbenannt')}")
                st.write(f"**Typ:** {spot.get('type', 'Unbekannt')} | **Diff:** {spot.get('diff', 'Medium')}")
                st.write(f"**Boden:** {spot.get('surface', 'Unbekannt')} | **Status:** {spot.get('status', 'Skatebar')}")
                st.write(f"**Crowd:** {spot.get('crowd', 'Unbekannt')}")
                
                tags = spot.get('tags', [])
                if tags:
                    st.write(f"**Tags:** {' '.join([f'`{t}`' for t in tags])}")
                
                if spot.get('clip'):
                    st.markdown(f"🎬 [Check Clip]({spot['clip']})")
                
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={spot['lat']},{spot['lon']}"
                st.markdown(f"[📍 Open in Google Maps]({google_maps_url})")
                
                st.write(f"Koordinaten: `{spot['lat']:.5f}, {spot['lon']:.5f}`")
                
                likes = spot.get('likes', 0)
                if st.button(f"❤️ {likes} Likes", key=f"like_{original_index}"):
                    spot['likes'] = likes + 1
                    save_data(st.session_state.spots)
                    st.rerun()
                
                if spot.get('photo') != "Kein Foto":
                    img_path = os.path.join("uploads", spot.get('photo'))
                    if os.path.exists(img_path):
                        st.image(img_path, caption=f"Spot-Foto", use_column_width=True)
                    else:
                        st.write(f"🖼️ Bild nicht gefunden: {spot.get('photo')}")
                
                if st.button(f"Spot löschen", key=f"del_{original_index}"):
                    st.session_state.spots.pop(original_index)
                    save_data(st.session_state.spots)
                    st.rerun()
else:
    st.info("Noch keine Spots markiert. Klicke auf die Karte, um zu starten!")
