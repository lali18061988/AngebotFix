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

# MODELL: Stabil und günstig (1.5 Flash)
MODEL_NAME = "gemini-1.5-flash-latest" 

# --- SESSION STATE INITIALISIEREN ---
# Das hier sorgt dafür, dass die App nicht vergisst, wer eingeloggt ist
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# --- FUNKTIONEN ---

def check_login(username, password):
    """Prüft, ob Datei existiert und Passwort stimmt."""
    filename = f"user_{username}.json"
    
    # Spezialfall: Demo-User wird automatisch erstellt, falls nicht da
    if username == "demo" and not os.path.exists(filename):
        create_demo_user()
    
    if not os.path.exists(filename):
        return False, "Benutzer nicht gefunden."
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # PASSWORT PRÜFUNG
        # Wir schauen, ob das Passwort in der Datei mit der Eingabe übereinstimmt
        stored_password = data.get("passwort")
        if stored_password == password:
            return True, data
        else:
            return False, "Falsches Passwort."
    except Exception as e:
        return False, f"Fehler in der Datei: {e}"

def create_demo_user():
    """Erstellt eine Demo-Datei mit Passwort 'demo'"""
    demo_data = {
        "passwort": "demo",  # DAS IST NEU
        "firma": "Musterhandwerk GmbH",
        "stundensatz": 65.00,
        "materialaufschlag_prozent": 15,
        "leistungen": {
            "wand_streichen_qm": 12.50,
            "anfahrt": 25.00
        }
    }
    with open("user_demo.json", "w", encoding="utf-8") as f:
        json.dump(demo_data, f, indent=4)

def get_gemini_response(prompt_parts):
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt_parts)
    return response.text

# --- APP STRUKTUR ---

# 1. LOGIN MASK (Wird angezeigt, wenn NICHT eingeloggt)
if not st.session_state.logged_in:
    st.title("🔐 Login AngebotFix")
    st.info("Bitte melde dich an, um auf deine Firmenpreise zuzugreifen.")
    
    col1, col2 = st.columns(2)
    with col1:
        inp_user = st.text_input("Benutzername")
    with col2:
        inp_pass = st.text_input("Passwort", type="password") # Versteckt die Eingabe
    
    if st.button("Anmelden"):
        success, result = check_login(inp_user, inp_pass)
        if success:
            st.session_state.logged_in = True
            st.session_state.user_data = result
            st.rerun() # Seite neu laden, um direkt zur App zu springen
        else:
            st.error(f"Login fehlgeschlagen: {result}")

# 2. HAUPT-APP (Wird nur angezeigt, WENN eingeloggt)
else:
    # Daten aus dem Session State holen
    user_data = st.session_state.user_data
    
    # Sidebar mit Logout
    st.sidebar.success(f"Firma: {user_data.get('firma')}")
    if st.sidebar.button("Abmelden"):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

    st.title("🔨 AngebotFix Pro")
    st.write(f"Willkommen, **{user_data.get('firma')}**!")
    st.info("Fülle mindestens EINES der Felder aus (Audio, Bild oder Text).")

    # --- EINGABE-BEREICH ---
    
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
            st.error("⚠️ Bitte gib uns etwas Futter! Sprich etwas auf, mach ein Foto oder tippe Text.")
        else:
            with st.spinner("KI kalkuliert mit deinen Preisen..."):
                
                # Wir löschen das Passwort aus den Daten, bevor wir sie an die KI senden (Sicherheit)
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
                    st.error(f"KI Fehler: {e}")
