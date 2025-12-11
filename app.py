import streamlit as st
import google.generativeai as genai
import json
import os
import tempfile
from PIL import Image

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="AngebotFix", page_icon="🛠️")

st.title("🛠️ AngebotFix - Der KI-Handwerker")

# --- API KEY SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("API Key fehlt! Bitte in den Streamlit Secrets hinterlegen.")
    st.stop()

# --- HILFSFUNKTION: MEDIEN HOCHLADEN ---
def upload_to_gemini(uploaded_file, mime_type):
    """Speichert Upload temporär und sendet ihn an Google AI"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{mime_type.split('/')[-1]}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    remote_file = genai.upload_file(tmp_path, mime_type=mime_type)
    return remote_file

# --- 1. LOGIN ---
st.header("1. Login")
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = None

user_code = st.text_input("Firmen-Code (z.B. user_demo):", key="login_input")

if st.button("Einloggen") or user_code:
    dateiname = f"{user_code}.json"
    if os.path.exists(dateiname):
        with open(dateiname, "r", encoding="utf-8") as f:
            st.session_state['user_data'] = json.load(f)
        st.success(f"Angemeldet: {st.session_state['user_data']['firma']}")
    elif user_code:
        st.error("Code nicht gefunden.")

# --- 2. DATENERFASSUNG (Nur wenn eingeloggt) ---
if st.session_state['user_data']:
    data = st.session_state['user_data']
    
    st.divider()
    st.header("2. Baustelle erfassen")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📸 Foto")
        img_input = st.camera_input("Foto der Baustelle machen")
        uploaded_img = st.file_uploader("Oder Bild hochladen", type=["jpg", "png", "jpeg"])
        
        # Priorisiere Kamera, sonst Upload
        final_image = img_input if img_input else uploaded_img

    with col2:
        st.info("🎤 Sprachnotiz")
        audio_input = st.audio_input("Sprich jetzt (Was ist zu tun?)")

    txt_input = st.text_area("Zusätzliche Notizen (optional)", placeholder="z.B. Bitte bis Freitag fertigstellen...")

    # --- 3. ANGEBOT GENERIEREN ---
    st.divider()
    st.header("3. Ergebnis")
    
    if st.button("✨ Angebot erstellen lassen", type="primary"):
        if not (final_image or audio_input or txt_input):
            st.warning("Bitte gib mindestens ein Foto, Audio oder Text ein.")
        else:
            with st.spinner("KI analysiert Preise, Foto und Sprache..."):
                try:
                    # Input-Liste für die KI vorbereiten
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    prompt_parts = []
                    
                    # 1. System-Anweisung & Preisliste
                    system_prompt = f"""
                    Du bist ein professioneller Handwerks-Assistent für die Firma '{data['firma']}' (Inhaber: {data['inhaber']}).
                    
                    DEINE AUFGABE:
                    Erstelle einen freundlichen, professionellen Angebotstext für einen Kunden basierend auf den Eingaben (Bild/Audio/Text).
                    
                    PREISLISTE (Nutze NUR diese Werte für Schätzungen):
                    Stundensatz: {data['stundensatz']} EUR
                    Materialaufschlag: {data['material_aufschlag']}
                    Mehrwertsteuer: {data['mwst']}%
                    Leistungen:
                    {json.dumps(data['leistungen'], indent=2)}
                    
                    ANWEISUNGEN:
                    1. Analysiere das Bild und das Audio, um herauszufinden, was getan werden muss.
                    2. Schätze die Mengen grob (z.B. Quadratmeter anhand des Bildes), wenn keine genannt werden.
                    3. Liste die Positionen tabellarisch auf mit Einzelpreis und Gesamtpreis.
                    4. Rechne korrekt! (Menge * Preis).
                    5. Sei höflich und direkt.
                    """
                    prompt_parts.append(system_prompt)

                    # 2. Bild hinzufügen (falls vorhanden)
                    if final_image:
                        # Bild laden für Gemini
                        img = Image.open(final_image)
                        prompt_parts.append(img)
                        prompt_parts.append("Hier ist ein Foto der Baustelle.")

                    # 3. Audio hinzufügen (falls vorhanden)
                    if audio_input:
                        st.text("Audio wird verarbeitet...")
                        remote_audio = upload_to_gemini(audio_input, mime_type="audio/wav")
                        prompt_parts.append(remote_audio)
                        prompt_parts.append("Hier sind die gesprochenen Anweisungen des Handwerkers.")

                    # 4. Text hinzufügen
                    if txt_input:
                        prompt_parts.append(f"Zusätzliche Notizen: {txt_input}")

                    # KI aufrufen
                    response = model.generate_content(prompt_parts)
                    
                    # Ergebnis anzeigen
                    st.markdown("### 📄 Angebots-Entwurf")
                    st.markdown(response.text)
                    
                    # Download Button simulieren (Text kopieren)
                    st.code(response.text, language="markdown")
                    
                except Exception as e:
                    st.error(f"Ein Fehler ist aufgetreten: {e}")
