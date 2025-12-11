import streamlit as st
import google.generativeai as genai
import json
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="AngebotFix", page_icon="🔨")

# 1. API Key Setup
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

# MODELL: Wir bleiben beim schnellen Flash 2.0
MODEL_NAME = "gemini-2.0-flash" 

# --- HILFSFUNKTIONEN (User Daten laden) ---
def load_user_data(username):
    filename = f"user_{username}.json"
    if not os.path.exists(filename):
        demo_data = {
            "firma": "Musterhandwerk GmbH",
            "stundensatz": 65.00,
            "materialaufschlag_prozent": 15,
            "leistungen": {
                "anfahrt": 25.00,
                "meisterstunde": 65.00,
                "gesellenstunde": 50.00,
                "material_pauschal": 10.00
            }
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(demo_data, f, indent=4)
        return demo_data
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def get_gemini_response(prompt_parts):
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt_parts)
    return response.text

# --- APP OBERFLÄCHE ---

st.title("🔨 AngebotFix Direkt")

# Login Simulation
username = st.sidebar.text_input("Benutzer", value="demo")
user_data = load_user_data(username)

if user_data:
    st.sidebar.success(f"Firma: {user_data.get('firma')}")
    # Preisliste in der Sidebar anzeigen (zur Kontrolle)
    with st.sidebar.expander("Preisliste"):
        st.json(user_data)
else:
    st.warning("Konnte Profildaten nicht laden.")
    st.stop()

st.write("### 1. Erfassung vor Ort")
st.info("Nimm die Baustelle auf: Sprich ins Mikro oder mach ein Foto.")

col1, col2 = st.columns(2)

with col1:
    st.write("**🎤 Sprachnotiz**")
    # DAS IST NEU: Das native Mikrofon-Widget
    audio_input = st.audio_input("Aufnahme starten")

with col2:
    st.write("**📸 Foto**")
    # DAS IST NEU: Das native Kamera-Widget
    camera_input = st.camera_input("Foto machen")

st.write("### 2. Zusätzliche Notizen (Optional)")
text_input = st.text_area("Tippen...", height=100, placeholder="Zusätzliche Infos hier tippen...")

# --- GENERIERUNG ---
if st.button("Angebot erstellen", type="primary"):
    
    if not audio_input and not camera_input and not text_input:
        st.error("Bitte gib erst Input (Foto, Audio oder Text)!")
    else:
        with st.spinner("KI wertet Kamera und Audio aus..."):
            
            # Prompt vorbereiten
            system_instruction = f"""
            Du bist ein Handwerks-Meister. Erstelle ein Angebot basierend auf den Eingaben.
            
            NUTZE DIESE PREISLISTE:
            {json.dumps(user_data, ensure_ascii=False)}
            
            REGELN:
            1. Höre dir das Audio an (falls vorhanden) und schaue das Bild an (falls vorhanden).
            2. Liste alle Arbeiten und Materialien auf.
            3. Berechne die Preise EXAKT nach der Preisliste oben.
            4. Wenn etwas fehlt, schätze fair und markiere es mit (*).
            5. Erstelle eine saubere Tabelle und einen kurzen, höflichen Text an den Kunden.
            """

            parts = [system_instruction]

            # Audio hinzufügen (Gemini nimmt Bytes direkt)
            if audio_input:
                parts.append({"mime_type": "audio/wav", "data": audio_input.getvalue()})
                parts.append("Hier ist die Sprachnotiz des Handwerkers.")

            # Bild hinzufügen
            if camera_input:
                parts.append({"mime_type": "image/jpeg", "data": camera_input.getvalue()})
                # ALTE ZEILE: parts.append("Hier ist das Foto der Baustelle.")
                # NEUE, BESSERE ZEILE:
                parts.append("Hier ist ein Foto. Das kann die Baustelle sein ODER ein Notizzettel. Lies unbedingt allen Text und alle Maße, die du auf dem Bild findest!")

            # Text hinzufügen
            if text_input:
                parts.append(f"Zusätzliche Notizen: {text_input}")

            try:
                # Ab an die KI
                result = get_gemini_response(parts)
                
                st.markdown("---")
                st.subheader("📝 Entwurf")
                st.markdown(result)
                
            except Exception as e:
                st.error(f"Fehler bei der KI-Verarbeitung: {e}")
