import os
import requests
import streamlit as st

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Fehler: SUPABASE_URL oder SUPABASE_KEY sind leer!")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"

def sign_up(email, password, username):
    """Erstellt einen neuen Account via direkter HTTP-API."""
    try:
        # 1. User in Supabase Auth erstellen
        res = requests.post(
            f"{AUTH_URL}/signup",
            headers=HEADERS,
            json={"email": email, "password": password}
        )
        
        if res.status_code == 200:
            data = res.json()
            user_id = data["user"]["id"]
            
            # 2. Standort-Eintrag in user_locations erstellen
            insert_headers = HEADERS.copy()
            insert_headers["Authorization"] = f"Bearer {data['access_token']}"
            
            insert_res = requests.post(
                f"{REST_URL}/user_locations",
                headers=insert_headers,
                json={
                    "user_id": user_id,
                    "username": username,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "status": "offline"
                }
            )
            
            if insert_res.status_code not in (200, 201):
                print(f"Insert warning: {insert_res.status_code} {insert_res.text}")
            
            return data, None
        else:
            return None, f"API Fehler ({res.status_code}): {res.json().get('message', res.text)}"
            
    except Exception as e:
        return None, f"Auth-Fehler: {str(e)}"

def sign_in(email, password):
    """Loggt den User ein via direkter HTTP-API."""
    try:
        res = requests.post(
            f"{AUTH_URL}/token?grant_type=password",
            headers=HEADERS,
            json={"email": email, "password": password}
        )
        
        if res.status_code == 200:
            return res, None
        else:
            err_msg = res.json().get('message', res.text) if res.text else "Unbekannter Fehler"
            return None, f"Login Fehler ({res.status_code}): {err_msg}"
            
    except Exception as e:
        return None, f"Login-Fehler: {str(e)}"

def update_my_location(user_id, username, lat, lon, status="online"):
    """Aktualisiert den eigenen Live-Standort in der DB."""
    try:
        # Hol den aktuellen Token (einfach mit anon key upsert)
        requests.patch(
            f"{REST_URL}/user_locations",
            params={"user_id": f"eq.{user_id}"},
            headers=HEADERS,
            json={
                "latitude": lat,
                "longitude": lon,
                "status": status,
                "updated_at": "now()"
            }
        )
    except Exception as e:
        print(f"Error updating location: {e}")

def get_all_live_locations():
    """Holt alle Nutzer, die gerade 'online' sind."""
    try:
        res = requests.get(
            f"{REST_URL}/user_locations",
            headers=HEADERS,
            params={"status": "eq.online", "select": "user_id,username,latitude,longitude"}
        )
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        print(f"Error fetching locations: {e}")
        return []
