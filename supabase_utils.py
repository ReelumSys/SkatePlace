import os
from supabase import create_client, Client
import streamlit as st

# In Streamlit Cloud nutzt man st.secrets anstatt .env für maximale Kompatibilität
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    # Fallback für lokale Entwicklung mit .env
    from dotenv import load_dotenv
    load_dotenv()
    URL = os.getenv("SUPABASE_URL")
    KEY = os.getenv("SUPABASE_KEY")

if not URL or not KEY:
    st.error("Supabase URL oder Key fehlt in den Secrets/Env!")

# Initialisiere Supabase Client
# Wir nutzen ein Try-Catch für den Client-Start, um API-Key Fehler abzufangen
try:
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Supabase Client Initialisierungsfehler: {e}")

def sign_up(email, password, username):
    """Erstellt einen neuen Account und initialisiert den Standort-Eintrag."""
    try:
        # Auth-Teil
        res = supabase.auth.sign_up({"email": email, "password": password})
        
        if res.user:
            user_id = res.user.id
            # Standort-Eintrag erstellen
            supabase.table("user_locations").insert({
                "user_id": user_id,
                "username": username,
                "latitude": 0.0,
                "longitude": 0.0,
                "status": "offline"
            }).execute()
            return res, None
        return None, "Fehler beim Erstellen des Users"
    except Exception as e:
        return None, f"Auth-Fehler: {str(e)}"

def sign_in(email, password):
    """Loggt den User ein."""
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, f"Login-Fehler: {str(e)}"

def update_my_location(user_id, username, lat, lon, status="online"):
    """Aktualisiert den eigenen Live-Standort in der DB."""
    try:
        supabase.table("user_locations").update({
            "latitude": lat,
            "longitude": lon,
            "status": status,
            "updated_at": "now()"
        }).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"Error updating location: {e}")

def get_all_live_locations():
    """Holt alle Nutzer, die gerade 'online' sind."""
    try:
        res = supabase.table("user_locations").select("*").eq("status", "online").execute()
        return res.data
    except Exception as e:
        print(f"Error fetching locations: {e}")
        return []
