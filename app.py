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
        st.error("Kein API Key in den Streamlit Secrets gefunden!")
        st.stop()
except Exception as e:
    st.error(f"Fehler bei der API Konfiguration: {e}")
    st.stop()

# --- MODELL AUSWAHL (HIER WAR DER FEHLER) ---
# Wir nutzen jetzt das Modell, das bei dir laut Diagnose funktioniert:
MODEL_NAME = "gemini-2.0-flash" 

# --- HILFSFUNKTIONEN ---

def load_user_data(username):
    """Lädt die Preisliste des Handwerkers aus einer JSON-Datei."""
    filename = f"user_{username}.json"
    
    # Für den ersten Start: Wenn die Datei nicht existiert, erstellen wir eine Demo-Datei
    if not os.path.exists(filename):
        demo_data = {
            "firma": "Musterhandwerk GmbH",
            "stundensatz": 65.00,
            "materialaufschlag_prozent": 15,
            "leistungen": {
                "anfahrt_pauschale": 25.00,
                "streichen_qm": 12.50,
                "boden_verlegen_qm": 35.00,
                "steckdose_montieren": 15.00
            }
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(demo_data, f, indent=4)
        return demo_data, True # True bedeutet: Datei wurde neu erstellt

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f), False
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei {filename}: {e}")
        return None, False

def get_gemini_response(prompt_parts):
    """Sendet Daten an Gemini 2.0 Flash"""
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt_parts)
    return response.text

# --- APP START ---

st.title("🔨 AngebotFix")
st.subheader("Automatischer Angebots-Generator für Handwerker")

# 1. Login (Simuliert über Dateinamen)
username = st.text_input("Benutzername (z.B. 'schmidt' oder 'demo')", value="demo")

if username:
    user_data, neu_erstellt = load_user_data(username)
    
    if neu_erstellt:
        st.info(f"Willkommen! Eine neue Profildatei 'user_{username}.json' wurde für dich angelegt.")
    
    if user_data:
        st.sidebar.success(f"Eingeloggt als: {user_data.get('firma', 'Unbekannt')}")
        st.sidebar.write(f"Stundensatz: {user_data.get('stundensatz')} €")
        
        with st.expander("Aktuelle Preisliste ansehen"):
            st.json(user_data)

        st.divider()

        # 2. Eingabe der Projektdaten
        st.write("### Projekt-Infos eingeben")
        
        col1, col2 = st.columns(2)
        with col1:
            input_text = st.text_area("Notizen / Anweisungen", height=150, 
                                    placeholder="Z.B.: Wohnzimmer streichen ca 40qm, 2 Steckdosen tauschen. Kunde Müller, Hauptstr. 1.")
        
        with col2:
            input_image = st.file_uploader("Foto hochladen (optional)", type=["jpg", "png", "jpeg"])
            # Audio Upload (Streamlit unterstützt Mikrofon-Aufnahme direkt oft nur via Plugin, 
            # Upload ist stabiler für den Start)
            input_audio = st.file_uploader("Sprachnotiz hochladen (optional)", type=["mp3", "wav", "m4a"])

        generate_btn = st.button("Angebot erstellen", type="primary")

        if generate_btn:
            if not input_text and not input_image and not input_audio:
                st.warning("Bitte gib mindestens Text, ein Bild oder Audio ein.")
            else:
                with st.spinner("KI berechnet Angebot basierend auf deinen Preisen..."):
                    
                    # Prompt zusammenbauen
                    # Wir übergeben die JSON-Daten als Kontext an die KI
                    system_instruction = f"""
                    Du bist ein Assistent für Handwerker. Deine Aufgabe ist es, ein professionelles Angebot zu schreiben.
                    Nutze DIESE Preisliste und Firmendaten für die Kalkulation (rechne exakt!):
                    {json.dumps(user_data, ensure_ascii=False)}

                    Anweisungen:
                    1. Analysiere den Input (Text, Bild oder Audio).
                    2. Identifiziere die Arbeitsleistungen und Materialien.
                    3. Ordne sie den Preisen in der Preisliste zu. Wenn etwas nicht in der Liste steht, schätze einen realistischen Preis und markiere ihn mit (*).
                    4. Erstelle eine tabellarische Auflistung mit Einzelpreisen und Gesamtpreis.
                    5. Formuliere einen freundlichen Anschreibentext dazu.
                    6. Gib das Ergebnis sauber formatiert aus.
                    """

                    # Liste der Inhalte für Gemini erstellen
                    prompt_parts = [system_instruction]
                    
                    if input_text:
                        prompt_parts.append(f"Hier sind die Notizen des Handwerkers: {input_text}")
                    
                    if input_image:
                        prompt_parts.append(input_image) # Bilddaten direkt übergeben
                        prompt_parts.append("Analysiere dieses Bild auf relevante Details für das Angebot.")
                    
                    if input_audio:
                        prompt_parts.append(input_audio) # Audiodaten direkt übergeben
                        prompt_parts.append("Höre dir diese Sprachnotiz an und extrahiere die Aufgaben.")

                    try:
                        # Anfrage senden
                        result = get_gemini_response(prompt_parts)
                        st.markdown("### Fertiger Entwurf:")
                        st.markdown(result)
                    except Exception as e:
                        st.error(f"Ein Fehler ist aufgetreten: {e}")
