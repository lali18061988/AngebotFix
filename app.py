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
        st.error("Kein API Key gefunden. Bitte in den Secrets hinterlegen.")
        st.stop()
except Exception as e:
    st.error(f"Fehler: {e}")
    st.stop()

# MODELL: 
MODEL_NAME = "gemini-2.0-flash"

# --- HILFSFUNKTIONEN ---

def load_user_data(username):
    """Lädt die individuelle Preisliste des Handwerkers."""
    filename = f"user_{username}.json"
    
    # Automatische Erstellung einer Demo-Datei, falls noch keine existiert
    if not os.path.exists(filename):
        demo_data = {
            "firma": "Musterhandwerk GmbH",
            "stundensatz": 65.00,
            "anfahrt_pauschal": 25.00,
            "materialaufschlag_prozent": 15,
            "leistungen": {
                "wand_streichen_qm": 12.50,
                "decke_streichen_qm": 14.00,
                "boden_verlegen_qm": 35.00,
                "steckdose_montieren_stk": 15.00,
                "wc_becken_montage_pauschal": 120.00
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

st.title("🔨 AngebotFix Pro")

# 1. Login Simulation (Lädt die JSON mit den Preisen)
username = st.sidebar.text_input("Benutzer-Kürzel", value="demo")
user_data = load_user_data(username)

if user_data:
    st.sidebar.success(f"Angemeldet: {user_data.get('firma')}")
    st.sidebar.info("Preise werden aus deiner JSON-Datei geladen.")
    with st.sidebar.expander("Deine Preisliste ansehen"):
        st.json(user_data)
else:
    st.warning("Konnte Profildaten nicht laden.")
    st.stop()

st.divider()
st.write("### 🆕 Neues Angebot erfassen")
st.info("Fülle mindestens EINES der Felder aus (Audio, Bild oder Text).")

# --- EINGABE-BEREICH ---

# A) AUDIO
st.subheader("1. 🎤 Sprachnotiz")
audio_input = st.audio_input("Aufnahme starten")

# B) BILD (Kamera ODER Upload)
st.subheader("2. 📸 Bild / Notiz")
tab1, tab2 = st.tabs(["Kamera nutzen", "Datei hochladen"])

with tab1:
    camera_input = st.camera_input("Foto machen")
with tab2:
    upload_input = st.file_uploader("Bild hochladen (z.B. aus Galerie)", type=["jpg", "png", "jpeg"])

# C) TEXT
st.subheader("3. 📝 Text / Hinweise")
text_input = st.text_area("Tippen...", height=100, placeholder="Z.B. Kunde Maier, 3. Stock, Aufzug vorhanden...")


# --- GENERIERUNG ---
st.divider()
if st.button("🚀 Angebot erstellen", type="primary"):
    
    # PRÜFUNG: Ist mindestens eine Info da?
    has_input = (audio_input is not None) or \
                (camera_input is not None) or \
                (upload_input is not None) or \
                (text_input.strip() != "")
    
    if not has_input:
        st.error("⚠️ Bitte gib uns etwas Futter! Sprich etwas auf, mach ein Foto oder tippe Text.")
    else:
        with st.spinner("KI analysiert deine Eingaben und kalkuliert Preise..."):
            
            # 1. System-Prompt bauen (Die "Gehirn"-Anweisung)
            system_instruction = f"""
            Du bist ein professioneller Handwerks-Meister. Erstelle ein Angebot basierend auf den Eingaben.
            
            WICHTIG - NUTZE AUSSCHLIESSLICH DIESE PREISLISTE ZUR KALKULATION:
            {json.dumps(user_data, ensure_ascii=False)}
            
            DEINE AUFGABE:
            1. Analysiere ALLE Eingaben (Audio, Bilder, Text) gleichzeitig.
               - Wenn ein Bild eine handgeschriebene Notiz ist: Lies die Maße und Aufgaben aus!
               - Wenn ein Bild den Raum zeigt: Schätze grob, falls keine Maße genannt wurden.
            2. Identifiziere die benötigten Leistungen aus der Preisliste.
            3. Berechne die Summen (Menge x Einzelpreis).
            4. Wenn eine Leistung NICHT in der Liste steht: Schätze einen marktüblichen Preis und markiere ihn deutlich mit (*).
            5. Erstelle eine saubere Tabelle und einen freundlichen Angebotstext.
            """

            parts = [system_instruction]

            # 2. Daten an die KI anhängen (nur was da ist)
            
            if audio_input:
                parts.append({"mime_type": "audio/wav", "data": audio_input.getvalue()})
                parts.append("Anweisung aus der Sprachnachricht:")

            if camera_input:
                parts.append({"mime_type": "image/jpeg", "data": camera_input.getvalue()})
                parts.append("Bild von der Kamera (beachte Notizen oder Raumsituation):")

            if upload_input:
                # Wir müssen den Mime-Type (jpg/png) erkennen
                parts.append({"mime_type": upload_input.type, "data": upload_input.getvalue()})
                parts.append("Hochgeladene Bild-Datei (beachte Notizen oder Raumsituation):")

            if text_input:
                parts.append(f"Zusätzliche schriftliche Notizen: {text_input}")

            try:
                # 3. Abflug!
                result = get_gemini_response(parts)
                
                st.markdown("### ✅ Fertiger Entwurf")
                st.markdown(result)
                
            except Exception as e:
                st.error(f"Hoppla, da gab es einen Fehler bei der KI: {e}")
