import streamlit as st
import google.generativeai as genai
import json
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="AngebotFix Pro", page_icon="🔨")

# API Key Setup
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("Kein API Key gefunden.")
        st.stop()
except Exception as e:
    st.error(f"Fehler: {e}")
    st.stop()

# MODELL: Wir gehen zurück zum STABILEN 1.5 Flash
# Das hat hohe Limits (15 Anfragen pro Minute kostenlos)
MODEL_NAME = "gemini-flash-latest" 

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# --- FUNKTIONEN ---

def check_login(username, password):
    filename = f"user_{username}.json"
    
    if username == "demo" and not os.path.exists(filename):
        create_demo_user()
    
    if not os.path.exists(filename):
        return False, "Benutzer nicht gefunden."
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        stored_password = data.get("passwort")
        if stored_password == password:
            return True, data
        else:
            return False, "Falsches Passwort."
    except Exception as e:
        return False, f"Fehler in der Datei: {e}"

def create_demo_user():
    demo_data = {
        "passwort": "demo",
        "firma": "Musterhandwerk GmbH",
        "stundensatz": 65.00,
        "materialaufschlag_prozent": 15,
        "leistungen": {
            "wand_streichen_qm": 12.50,
            "anfahrt_pauschal": 25.00,
            "steckdose_wechseln": 15.00
        }
    }
    with open("user_demo.json", "w", encoding="utf-8") as f:
        json.dump(demo_data, f, indent=4)

def get_gemini_response(prompt_parts):
    # Wir erstellen das Modell hier frisch
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt_parts)
    return response.text

# --- APP ---

if not st.session_state.logged_in:
    st.title("🔐 Login AngebotFix")
    st.info("Bitte anmelden (Demo: demo / demo)")
    
    col1, col2 = st.columns(2)
    with col1:
        inp_user = st.text_input("Benutzername")
    with col2:
        inp_pass = st.text_input("Passwort", type="password")
    
    if st.button("Anmelden"):
        success, result = check_login(inp_user, inp_pass)
        if success:
            st.session_state.logged_in = True
            st.session_state.user_data = result
            st.rerun()
        else:
            st.error(f"Login fehlgeschlagen: {result}")

else:
    user_data = st.session_state.user_data
    
    st.sidebar.success(f"Firma: {user_data.get('firma')}")
    if st.sidebar.button("Abmelden"):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

    st.title("🔨 AngebotFix Pro")
    st.write(f"Moin, **{user_data.get('firma')}**!")
    st.info("Erfasse dein Angebot:")

    # --- EINGABE ---
    
    st.subheader("1. 🎤 Sprachnotiz")
    audio_input = st.audio_input("Aufnahme starten")

    st.subheader("2. 📸 Bild / Notiz")
    tab1, tab2 = st.tabs(["Kamera nutzen", "Datei hochladen"])
    with tab1:
        camera_input = st.camera_input("Foto machen")
    with tab2:
        upload_input = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])

    st.subheader("3. 📝 Text / Hinweise")
    text_input = st.text_area("Tippen...", height=100)

    # --- GENERIERUNG ---
    st.divider()
    if st.button("🚀 Angebot erstellen", type="primary"):
        
        has_input = (audio_input is not None) or \
                    (camera_input is not None) or \
                    (upload_input is not None) or \
                    (text_input.strip() != "")
        
        if not has_input:
            st.error("⚠️ Bitte gib Input: Audio, Foto oder Text.")
        else:
            with st.spinner("KI kalkuliert..."):
                
                # Passwort entfernen für Sicherheit
                safe_user_data = user_data.copy()
                if "passwort" in safe_user_data:
                    del safe_user_data["passwort"]

                system_instruction = f"""
                Du bist ein professioneller Handwerks-Meister. Erstelle ein Angebot.
                
                NUTZE AUSSCHLIESSLICH DIESE PREISLISTE:
                {json.dumps(safe_user_data, ensure_ascii=False)}
                
                ANWEISUNG:
                1. Analysiere Audio, Bilder und Text.
                2. Erstelle eine Tabelle mit Positionen, Mengen, Einzelpreis und Gesamtpreis.
                3. Rechne EXAKT.
                4. Schreibe einen freundlichen Angebotstext.
                """

                parts = [system_instruction]
                
                if audio_input:
                    parts.append({"mime_type": "audio/wav", "data": audio_input.getvalue()})
                    parts.append("Sprachnotiz:")
                if camera_input:
                    parts.append({"mime_type": "image/jpeg", "data": camera_input.getvalue()})
                    parts.append("Kamera-Bild:")
                if upload_input:
                    parts.append({"mime_type": upload_input.type, "data": upload_input.getvalue()})
                    parts.append("Upload-Bild:")
                if text_input:
                    parts.append(f"Notizen: {text_input}")

                try:
                    result = get_gemini_response(parts)
                    st.markdown("### ✅ Fertiger Entwurf")
                    st.markdown(result)
                except Exception as e:
                    # Fehlermeldung schöner formatieren
                    st.error("Es gab ein Problem. Falls Fehler 404 kommt, wird die Bibliothek gerade aktualisiert.")
                    st.code(str(e))
