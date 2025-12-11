import streamlit as st
import google.generativeai as genai
import importlib.metadata

st.title("🔍 Diagnose-Modus")

# 1. Version prüfen
try:
    version = importlib.metadata.version("google-generativeai")
    st.info(f"Installierte Google-Bibliothek Version: {version}")
except:
    st.warning("Konnte Version nicht lesen.")

# 2. Verbindung und Modelle prüfen
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("Frage Google nach verfügbaren Modellen...")
    
    models = list(genai.list_models())
    
    found_flash = False
    for m in models:
        st.text(f"Gefunden: {m.name}")
        if "flash" in m.name:
            found_flash = True
            st.success(f"HA! Flash ist hier verfügbar als: {m.name}")

    if not found_flash:
        st.error("Kein 'Flash' Modell in der Liste gefunden.")

except Exception as e:
    st.error(f"Genereller Fehler: {e}")
