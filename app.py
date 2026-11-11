import importlib
import os
import openai
import streamlit as st
from google import genai
from google.genai import types

# 1. Page Configuration & Language State Setup
st.set_page_config(page_title="Holiday Roast Calculator", page_icon="🦃", layout="centered")

if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# Language Toggle Function
def toggle_language():
    st.session_state.lang = "DE" if st.session_state.lang == "EN" else "EN"

# 2. Translation Dictionary
ui = {
    "EN": {
        "title": "🦃 Holiday Roast & Timeline Calculator",
        "subtitle": "Calculate your perfect turkey timeline and prep down to the minute.",
        "btn_lang": "Auf Deutsch anzeigen 🇩🇪",
        "lbl_weight": "Turkey Weight (in kg)",
        "lbl_time": "Target Dining Time (24-hour format)",
        "btn_calc": "Generate Printable Schedule",
        "api_error": "Please configure your GEMINI_API_KEY environment variable or enter it in the sidebar.",
        "loading": "Calculating culinary logistics...",
    },
    "DE": {
        "title": "🦃 Festtagsbraten & Zeitplan-Rechner",
        "subtitle": "Berechnen Sie Ihren perfekten Puten-Zeitplan und Vorbereitung auf die Minute genau.",
        "btn_lang": "Switch to English 🇬🇧",
        "lbl_weight": "Gewicht der Pute/Truthahn (in kg)",
        "lbl_time": "Geplante Essenszeit (24-Stunden-Format)",
        "btn_calc": "Druckbaren Zeitplan generieren",
        "api_error": "Bitte konfigurieren Sie Ihre GEMINI_API_KEY Umgebungsvariable oder tragen Sie sie in der Seitenleiste ein.",
        "loading": "Kulinarische Logistik wird berechnet...",
    }
}

current_lang = st.session_state.lang

# Top Row: Title and Language Switcher Button
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title(ui[current_lang]["title"])
    st.write(ui[current_lang]["subtitle"])
with col_btn:
    st.button(ui[current_lang]["btn_lang"], on_click=toggle_language)

st.divider()

# 3. Sidebar API Key handling (for easy sharing)
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# 4. User Inputs
col1, col2 = st.columns(2)
with col1:
    turkey_weight = st.number_input(ui[current_lang]["lbl_weight"], min_value=2.0, max_value=20.0, value=5.3, step=0.1)
with col2:
    dining_time = st.time_input(ui[current_lang]["lbl_time"], value=types.datetime.time(12, 30))

formatted_time = dining_time.strftime("%H:%M")

# 5. App Processing Logic
if st.button(ui[current_lang]["btn_calc"], type="primary"):
    if not api_key:
        st.error(ui[current_lang]["api_error"])
    else:
        with st.spinner(ui[current_lang]["loading"]):
            response_text = ""
            user_prompt = (
                f"Generate schedule for a {turkey_weight}kg turkey targeting a completion time of {formatted_time}."
            )

            try:
                # Initialize the official Google GenAI Client
                client = genai.Client(api_key=api_key)

                # Base System Prompt injected with the active output language instruction
                system_instruction = f"""
                You are an expert culinary assistant specialized in holiday roasting and baking logistics. Your sole purpose is to help users calculate precise, step-by-step preparation timelines and ingredient scaling for Holiday Turkeys and classic British desserts (like Sticky Toffee Pudding) adapted for local supermarkets (such as Germany).

                OUTPUT LANGUAGE RULE:
                You must write the entire output report completely in this language: {"English" if current_lang == "EN" else "German"}.

                The user will provide two main inputs:
                1. Turkey Weight (in kg)
                2. Target Dining Time (e.g., 12:30 PM or 18:00)

                Your output must be a highly structured, clean, and printable timeline formatted in Markdown. Do not include conversational filler, chatty preambles, or unformatted text. Start directly with the document header.

                ### CORE MATHEMATICAL CALCULATIONS
                1. Wet Brine Volume & Ratios:
                   - Solution Volume: Calculate 1 Liter of water per 1 kg of turkey weight (round up to the nearest whole liter, minimum 4L).
                   - Salt Ratio: Use a 6% salt-to-water solution. (Multiply calculated Liters of water by 60 grams of salt).
                   - Sugar Ratio: Use half the weight of the salt (Multiply calculated Liters of water by 30 grams of sugar).
                2. Honey-Butter Layer Ratios:
                   - For every 1 kg of turkey, allocate 30g of unsalted butter and 12g of fluid honey. Include seasonal fresh herbs (thyme/rosemary).
                3. Roasting & Resting Logistics:
                   - Initial Blast: 30 minutes at 200°C (390°F) Ober-/Unterhitze.
                   - Main Roast Time: Calculate 30 to 35 minutes per kg of total turkey weight at 160°C (320°F).
                   - Target Internal Temp: Must reach 75°C (165°F) in the thickest part of the thigh.
                   - Resting Window: Mandate exactly 45 minutes of undisturbed rest post-roasting before carving.
                4. Timeline Backward-Engineering:
                   - Take the user's input "Target Dining Time" and subtract the exact sum of: Main Roast Time + 30 Mins (Initial Blast) + 45 Mins (Rest Time) + 30 Mins (Chilling Buffer/Prep).
                   - Chart every milestone chronologically from the Friday evening brine setup to the moment of carving.

                ### REGIONAL LOCALIZATION INSTRUCTIONS (GERMANY)
                Always provide local German grocery naming conventions alongside English terms where appropriate (e.g. Speisesalz, Natron, Weizenmehl 405, Backpulver, Schlagsahne).

                ### OUTPUT PRINT LAYOUT REQUIREMENT
                Format your entire response using Markdown headers (###), bold text anchors for time-stamps (e.g., **09:15**), and clean, bordered tables for ingredient cross-references. Ensure there are distinct sections for the shopping list and chronology so it is clear when printed.
                """

                # --- TIER 1: Try Gemini Flash (Primary) ---
                try:
                    response = client.models.generate_content(
                        model=st.secrets.get("GEMINI_MODEL_NAME", "gemini-3.8-flash"),
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2
                        )
                    )
                    response_text = response.text
                    st.success("🤖 Powered by Gemini Flash")

                except Exception as e:
                    # If Gemini Flash hits a 503 error, don't crash! Trigger fallback.
                    st.warning("⚠️ Gemini Flash is currently busy. Trying fallback model...")

                    # --- TIER 2: Fallback to Gemini Pro ---
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-pro",
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.2
                            )
                        )
                        response_text = response.text
                        st.success("🚀 Powered by Gemini Pro (Fallback)")

                    except Exception as pro_error:
                        # --- TIER 3: Fallback to External Provider (OpenAI) ---
                        openai_key = st.secrets.get("OPENAI_API_KEY", "")

                        if openai_key:
                            try:
                                import openai

                                st.warning("⚠️ Google AI is entirely overloaded. Routing to OpenAI...")
                                openai_client = openai.OpenAI(api_key=openai_key)
                                openai_response = openai_client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {"role": "system", "content": system_instruction},
                                        {"role": "user", "content": user_prompt}
                                    ],
                                    temperature=0.2
                                )
                                response_text = openai_response.choices[0].message.content
                                st.success("🤖 Powered by OpenAI GPT-4o-mini (Emergency Fallback)")

                            except Exception as oa_error:
                                st.error(f"All model endpoints failed. OpenAI Error: {str(oa_error)}")
                        else:
                            st.error(
                                "Gemini endpoints are down (503), and no secondary provider API key was configured. Please try again in a few moments."
                            )

            except Exception as init_error:
                st.error(f"AI request failed: {str(init_error)}")

            # If any model succeeded, render the text layout cleanly
            if response_text:
                st.markdown(response_text)
                st.info("💡 Tip: Press Ctrl+P (Windows) or Cmd+P (Mac) to save this page layout cleanly as a PDF file!")
