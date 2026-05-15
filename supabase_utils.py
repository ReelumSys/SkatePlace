import os
from supabase import create_client, Client
import streamlit as st

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    from dotenv import load_dotenv
    load_dotenv()
    URL = os.getenv("SUPABASE_URL")
    KEY = os.getenv("SUPABASE_KEY")

if not URL or not KEY:
    st.error("Fehler: SUPABASE_URL oder SUPABASE_KEY sind leer!")
else:
    # Debug: Zeige nur Länge und letzte 4 Zeichen des Keys (sicherheitshalber)
    key_length = len(KEY)
    key_end = KEY[-4:] if len(KEY) > 4 else KEY
    st.info(f"Debug: URL={URL[:10]}..., KEY Länge={key_length}, KEY endet auf ...{key_end}")

try:
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Supabase Client Init Fehler: {e}")

def sign_up(email, password, username):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            user_id = res.user.id
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
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        # Gibt den kompletten Error-Text aus, damit wir wissen, was Supabase antwortet
        full_error = str(e)
        # Versuche Status-Code zu extrahieren, falls vorhanden
        status_info = ""
        if hasattr(e, 'status_code'):
            status_info = f" (HTTP Status: {e.status_code})"
        elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            status_info = f" (HTTP Status: {e.response.status_code})"
        return None, f"Login-Fehler{status_info}: {full_error}"

def update_my_location(user_id, username, lat, lon, status="online"):
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
    try:
        res = supabase.table("user_locations").select("*").eq("status", "online").execute()
        return res.data
    except Exception as e:
        print(f"Error fetching locations: {e}")
        return []
