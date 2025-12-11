import streamlit as st
import google.generativeai as genai
import json
import os

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="AngebotFix", page_icon="🛠️")

st.title("🛠️ AngebotFix - KI Assistent")

# --- API KEY SETUP ---
# Wir holen den Key sicher aus den Streamlit Secrets (wird gleich eingerichtet)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("API Key fehlt! Bitte in den Streamlit Secrets hinterlegen.")
    st.stop()

# --- LOGIN / DATEN LADEN ---
st.subheader("1. Login")
user_code = st.text_input("Bitte Firmen-Code eingeben (Dateiname ohne .json):", placeholder="z.B. user_demo")

if user_code:
    dateiname = f"{user_code}.json"
    
    # Prüfen ob Datei existiert
    if os.path.exists(dateiname):
        with open(dateiname, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        
        st.success(f"Angemeldet als: {user_data['firma']} ({user_data['inhaber']})")
        
        # Daten in der Session speichern (für später)
        st.session_state['user_data'] = user_data
        
        # --- TEST DER KI ---
        st.divider()
        st.subheader("System-Check")
        if st.button("Verbindung zur KI testen"):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Sage 'Hallo Handwerker!' und nenne ein zufälliges Werkzeug.")
                st.info(f"KI Antwortet: {response.text}")
            except Exception as e:
                st.error(f"Fehler bei KI Verbindung: {e}")

    else:
        st.warning("Firmen-Code nicht gefunden. Versuche 'user_demo'.")
