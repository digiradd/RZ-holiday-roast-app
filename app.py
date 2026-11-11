"""
Holiday Roast & Timeline Calculator
-----------------------------------
Python does all the maths (quantities + clock times) so the schedule is always
correct and identical between runs. The AI only writes the shopping list and
chef's notes around those fixed numbers. If no AI is available, the core
schedule still works.
"""

import datetime
import math
import os

import streamlit as st

# ---------------------------------------------------------------------------
# 1. Constants (change cooking rules here, not in the prompt)
# ---------------------------------------------------------------------------
BRINE_L_PER_KG = 1.0       # litres of water per kg turkey
BRINE_MIN_L = 4            # minimum brine volume
SALT_G_PER_L = 60          # 6 % brine
SUGAR_G_PER_L = 30         # half the salt
BUTTER_G_PER_KG = 30
HONEY_G_PER_KG = 12

BLAST_MIN = 30             # 200 °C initial blast
ROAST_MIN_PER_KG = 35      # planning value (upper end of 30–35 min/kg)
CHECK_MIN_PER_KG = 30      # start probing at the lower end
REST_MIN = 45
PREP_BUFFER_MIN = 30       # out of brine, pat dry, honey-butter, preheat
BRINE_HOURS = 12
BRINE_MIX_LEAD_MIN = 120   # make brine and let it cool fully before use


DEFAULT_FLASH_MODEL = "gemini-3.7-flash"
DEFAULT_PRO_MODEL = "gemini-2.5-pro"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"   # override via OPENAI_MODEL_NAME secret


# ---------------------------------------------------------------------------
# 2. Helpers
# ---------------------------------------------------------------------------
def get_secret(name: str, default: str = "") -> str:
    """Env var first, then Streamlit secrets. Never crashes if secrets.toml is missing."""
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


# ---------------------------------------------------------------------------
# 3. Page config, styling, language state
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Holiday Roast Calculator", page_icon="🦃", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #3A0606 0%, #1A0D00 100%); }
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="number-input"] {
        background-color: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px;
    }
    button[kind="primary"] {
        background-color: #A32A2A !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
        width: 100%;
    }
    /* Clean print: white page, black text, no sidebar/buttons */
    @media print {
        .stApp { background: white !important; }
        .stApp * { color: black !important; }
        section[data-testid="stSidebar"], header, button, .no-print { display: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "lang" not in st.session_state:
    st.session_state.lang = "EN"


def toggle_language():
    st.session_state.lang = "DE" if st.session_state.lang == "EN" else "EN"


ui = {
    "EN": {
        "title": "🦃 Holiday Roast & Timeline Calculator",
        "subtitle": "Calculate your perfect turkey timeline and prep down to the minute.",
        "btn_lang": "Auf Deutsch anzeigen 🇩🇪",
        "lbl_weight": "Turkey weight (kg)",
        "lbl_time": "Target dining time (24h)",
        "btn_calc": "Generate printable schedule",
        "sidebar_key": "Gemini API key (optional)",
        "no_key": "No API key set: showing the calculated schedule only. Add a GEMINI_API_KEY for the shopping list and chef's notes.",
        "loading": "Writing shopping list and chef's notes...",
        "tip": "💡 Download the schedule below, or press Ctrl+P / Cmd+P to print this page.",
        "banner": "🧑‍🍳 Holiday hosting tip: order your turkey early and make sure it fits in your fridge for brining!",
        "download": "⬇️ Download schedule (Markdown)",
        "powered": "🤖 Notes written by {model}",
        "fallback": "⚠️ {model} failed ({reason}). Trying the next option...",
        "all_failed": "All AI options failed. The calculated schedule above is still correct and complete.",
        "error_details": "Error details",
        "doc_title": "Holiday Roast Plan",
        "h_quantities": "Quantities",
        "h_timeline": "Timeline",
        "h_notes": "Shopping List & Chef's Notes",
        "col_item": "Item",
        "col_amount": "Amount",
        "col_time": "Time",
        "col_step": "Step",
        "phase": {0: "The Day of the Feast", -1: "The Day Before (Prep Day)", -2: "Two Days Before"},
        "items": {
            "water": "Water (brine)",
            "salt": "Salt (Speisesalz, non-iodised)",
            "sugar": "Sugar (Zucker)",
            "butter": "Unsalted butter (Süßrahmbutter, ungesalzen)",
            "honey": "Runny honey (flüssiger Honig)",
            "herbs": "Fresh thyme & rosemary",
        },
        "steps": {
            "brine_mix": "Mix brine: dissolve {salt} g salt and {sugar} g sugar in {water} L water. Cool completely.",
            "brine_in": "Turkey into the cold brine, fully submerged. Refrigerate ({hours} h).",
            "prep": "Out of the brine, rinse, pat very dry. Spread honey-butter under and over the skin. Preheat oven to 200 °C Ober-/Unterhitze.",
            "blast": "Turkey in: 200 °C blast for {blast} min.",
            "main": "Reduce to 160 °C. Main roast (planned {roast} min).",
            "check": "Start probing the thickest part of the thigh: target 75 °C.",
            "out": "Turkey out. Rest {rest} min, loosely covered, undisturbed.",
            "carve": "Carve and serve. 🎉",
        },
        "unit_l": "L",
    },
    "DE": {
        "title": "🦃 Festtagsbraten & Zeitplan-Rechner",
        "subtitle": "Berechnen Sie Ihren perfekten Puten-Zeitplan und die Vorbereitung auf die Minute genau.",
        "btn_lang": "Switch to English 🇬🇧",
        "lbl_weight": "Gewicht der Pute (kg)",
        "lbl_time": "Geplante Essenszeit (24h)",
        "btn_calc": "Druckbaren Zeitplan generieren",
        "sidebar_key": "Gemini API-Schlüssel (optional)",
        "no_key": "Kein API-Schlüssel gesetzt: Es wird nur der berechnete Zeitplan angezeigt. Mit GEMINI_API_KEY gibt es zusätzlich Einkaufsliste und Küchennotizen.",
        "loading": "Einkaufsliste und Küchennotizen werden geschrieben...",
        "tip": "💡 Laden Sie den Zeitplan unten herunter oder drucken Sie die Seite mit Strg+P / Cmd+P.",
        "banner": "🧑‍🍳 Festtags-Tipp: Bestellen Sie Ihre Pute frühzeitig und prüfen Sie, ob sie zum Pökeln in den Kühlschrank passt!",
        "download": "⬇️ Zeitplan herunterladen (Markdown)",
        "powered": "🤖 Notizen erstellt von {model}",
        "fallback": "⚠️ {model} fehlgeschlagen ({reason}). Nächste Option wird versucht...",
        "all_failed": "Alle KI-Optionen sind fehlgeschlagen. Der berechnete Zeitplan oben ist trotzdem korrekt und vollständig.",
        "error_details": "Fehlerdetails",
        "doc_title": "Festtagsbraten-Plan",
        "h_quantities": "Mengen",
        "h_timeline": "Zeitplan",
        "h_notes": "Einkaufsliste & Küchennotizen",
        "col_item": "Zutat",
        "col_amount": "Menge",
        "col_time": "Uhrzeit",
        "col_step": "Schritt",
        "phase": {0: "Der Festtag", -1: "Der Vortag (Vorbereitungstag)", -2: "Zwei Tage vorher"},
        "items": {
            "water": "Wasser (Lake)",
            "salt": "Speisesalz (ohne Jod)",
            "sugar": "Zucker",
            "butter": "Süßrahmbutter, ungesalzen",
            "honey": "Flüssiger Honig",
            "herbs": "Frischer Thymian & Rosmarin",
        },
        "steps": {
            "brine_mix": "Lake ansetzen: {salt} g Salz und {sugar} g Zucker in {water} L Wasser auflösen. Vollständig abkühlen lassen.",
            "brine_in": "Pute vollständig in die kalte Lake legen. Kühl stellen ({hours} Std.).",
            "prep": "Pute aus der Lake nehmen, abspülen, sehr gut trocken tupfen. Honigbutter unter und auf die Haut streichen. Ofen auf 200 °C Ober-/Unterhitze vorheizen.",
            "blast": "Pute in den Ofen: {blast} Min. bei 200 °C anbraten.",
            "main": "Auf 160 °C reduzieren. Hauptgarzeit (geplant {roast} Min.).",
            "check": "Kerntemperatur an der dicksten Stelle der Keule prüfen: Ziel 75 °C.",
            "out": "Pute herausnehmen. {rest} Min. locker abgedeckt ruhen lassen.",
            "carve": "Tranchieren und servieren. 🎉",
        },
        "unit_l": "L",
    },
}

lang = st.session_state.lang
t = ui[lang]


# ---------------------------------------------------------------------------
# 4. Deterministic calculations
# ---------------------------------------------------------------------------
def calc_quantities(weight_kg: float) -> dict:
    water_l = max(BRINE_MIN_L, math.ceil(weight_kg * BRINE_L_PER_KG))
    return {
        "water_l": water_l,
        "salt_g": water_l * SALT_G_PER_L,
        "sugar_g": water_l * SUGAR_G_PER_L,
        "butter_g": round(weight_kg * BUTTER_G_PER_KG),
        "honey_g": round(weight_kg * HONEY_G_PER_KG),
        "roast_min": math.ceil(weight_kg * ROAST_MIN_PER_KG),
        "check_after_min": math.ceil(weight_kg * CHECK_MIN_PER_KG),
    }


def build_timeline(weight_kg: float, dining: datetime.time, q: dict) -> list[tuple[datetime.datetime, str, int]]:
    """Work backwards from dining time. Returns (datetime, step_key, day_offset) sorted chronologically.
    Day-agnostic: everything is relative to a dummy feast date; phases are derived from
    the day offset, so no weekday names can ever appear."""
    feast_date = datetime.date(2000, 1, 10)  # arbitrary anchor, never shown
    serve = datetime.datetime.combine(feast_date, dining)
    m = lambda n: datetime.timedelta(minutes=n)

    out_of_oven = serve - m(REST_MIN)
    main_start = out_of_oven - m(q["roast_min"])
    blast_start = main_start - m(BLAST_MIN)
    prep_start = blast_start - m(PREP_BUFFER_MIN)
    brine_in = prep_start - m(BRINE_HOURS * 60)
    brine_in -= m(brine_in.minute % 15)  # round down to a friendly quarter hour (brines a bit longer)
    brine_mix = brine_in - m(BRINE_MIX_LEAD_MIN)
    check = main_start + m(q["check_after_min"])
    
    events = [
        (brine_mix, "brine_mix"),
        (brine_in, "brine_in"),
        (prep_start, "prep"),
        (blast_start, "blast"),
        (main_start, "main"),
        (check, "check"),
        (out_of_oven, "out"),
        (serve, "carve"),
    ]
    events.sort(key=lambda e: e[0])
    return [(dt, key, (dt.date() - feast_date).days) for dt, key in events]


def render_markdown(weight_kg, dining, q, timeline, t) -> str:
    """Single source of truth for screen, download and AI prompt."""
    fmt = dict(
        salt=q["salt_g"], sugar=q["sugar_g"], water=q["water_l"], hours=BRINE_HOURS,
        blast=BLAST_MIN, roast=q["roast_min"], rest=REST_MIN,
    )
    lines = [f"## {t['doc_title']}: {weight_kg:.1f} kg · {dining.strftime('%H:%M')}", ""]

    lines += [f"### {t['h_quantities']}", "", f"| {t['col_item']} | {t['col_amount']} |", "|---|---|"]
    items = t["items"]
    lines += [
        f"| {items['water']} | {q['water_l']} {t['unit_l']} |",
        f"| {items['salt']} | {q['salt_g']} g |",
        f"| {items['sugar']} | {q['sugar_g']} g |",
        f"| {items['butter']} | {q['butter_g']} g |",
        f"| {items['honey']} | {q['honey_g']} g |",
        f"| {items['herbs']} | ✓ |",
        "",
    ]

    lines += [f"### {t['h_timeline']}", ""]
    current_phase = None
    for dt, key, offset in timeline:
        phase = t["phase"].get(offset, t["phase"][-2])
        if phase != current_phase:
            lines += ["", f"#### {phase}", "", f"| {t['col_time']} | {t['col_step']} |", "|---|---|"]
            current_phase = phase
        lines.append(f"| **{dt.strftime('%H:%M')}** | {t['steps'][key].format(**fmt)} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. AI layer (notes only, numbers are locked)
# ---------------------------------------------------------------------------
def build_system_instruction(lang_name: str, t: dict) -> str:
    return f"""
You are an expert culinary assistant for holiday roasting and baking, adapting recipes to German supermarkets.

LANGUAGE: Write everything in {lang_name}.

You receive a finished, already-calculated roast plan. The quantities and clock times in it are FINAL.
- Never change, recalculate or contradict any number or time.
- Never mention weekday names (Monday, Freitag, etc.). Refer to days only as
  "{t['phase'][-1]}" and "{t['phase'][0]}".
- No chatty preamble. Start directly with the first heading.

Write ONLY these two sections in Markdown:

### 🛒 Shopping list
A bordered table grouped by store section, covering the turkey plan. Show English name and German supermarket
name side by side (e.g. salt → Speisesalz ohne Jod, unsalted butter → Süßrahmbutter ungesalzen,
runny honey → flüssiger Honig). Use the exact quantities from the plan for the turkey items.

### 👨‍🍳 Chef's notes
5 to 8 short, practical bullet points: brining container/fridge space, food safety,
resting, gravy from the drippings.
"""


def try_gemini(model: str, api_key: str, system_instruction: str, user_prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2),
    )
    if not response.text:
        raise RuntimeError("Empty response")
    return response.text


def try_openai(model: str, api_key: str, system_instruction: str, user_prompt: str) -> str:
    import openai  # add `openai` to requirements.txt if you use this fallback

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("Empty response")
    return text


def short_reason(err: Exception) -> str:
    msg = str(err).lower()
    if "api key" in msg or "401" in msg or "403" in msg or "permission" in msg:
        return "invalid API key"
    if "404" in msg or "not found" in msg:
        return "model not found"
    if "429" in msg or "quota" in msg or "rate" in msg:
        return "quota / rate limit"
    if "503" in msg or "overloaded" in msg or "unavailable" in msg:
        return "busy"
    return type(err).__name__


def generate_notes(plan_md: str, t: dict, lang_name: str, gemini_key: str):
    """Walk the fallback chain. Returns (text, model, errors); text/model are None if all fail."""
    system_instruction = build_system_instruction(lang_name, t)
    user_prompt = f"Here is the final plan:\n\n{plan_md}"

    chain = []
    if gemini_key:
        chain.append(("gemini", get_secret("GEMINI_MODEL_NAME", DEFAULT_FLASH_MODEL), gemini_key))
        chain.append(("gemini", DEFAULT_PRO_MODEL, gemini_key))
    openai_key = get_secret("OPENAI_API_KEY")
    if openai_key:
        chain.append(("openai", get_secret("OPENAI_MODEL_NAME", DEFAULT_OPENAI_MODEL), openai_key))

    errors = []
    for provider, model, key in chain:
        try:
            fn = try_gemini if provider == "gemini" else try_openai
            return fn(model, key, system_instruction, user_prompt), model, errors
        except Exception as e:
            errors.append(f"{model}: {e}")
            st.warning(t["fallback"].format(model=model, reason=short_reason(e)))
    return None, None, errors


# ---------------------------------------------------------------------------
# 6. Layout
# ---------------------------------------------------------------------------
st.markdown("### 🍂 🦃 🥧 🎄 ❄️")

col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title(t["title"])
    st.write(t["subtitle"])
with col_btn:
    st.write("")
    st.button(t["btn_lang"], on_click=toggle_language)

st.markdown(
    f"""
    <div style="background-color: rgba(163, 42, 42, 0.2); padding: 15px; border-left: 5px solid #A32A2A;
                border-radius: 4px; margin-bottom: 20px;">
        <strong>{t["banner"]}</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

gemini_key = get_secret("GEMINI_API_KEY")
if not gemini_key:
    gemini_key = st.sidebar.text_input(t["sidebar_key"], type="password")

col1, col2 = st.columns(2)
with col1:
    turkey_weight = st.number_input(t["lbl_weight"], min_value=2.0, max_value=20.0, value=5.3, step=0.1)
with col2:
    dining_time = st.time_input(t["lbl_time"], value=datetime.time(12, 30), step=datetime.timedelta(minutes=15))

# Schedule is cheap and deterministic: always computed, in the current language.
q = calc_quantities(turkey_weight)
timeline = build_timeline(turkey_weight, dining_time, q)
plan_md = render_markdown(turkey_weight, dining_time, q, timeline, t)

# AI notes are cached per (weight, time, language) so reruns don't cost API calls.
cache_key = (round(turkey_weight, 1), dining_time.strftime("%H:%M"), lang)
if "notes" not in st.session_state:
    st.session_state.notes = {}

if st.button(t["btn_calc"], type="primary"):
    if not gemini_key and not get_secret("OPENAI_API_KEY"):
        st.info(t["no_key"])
    else:
        with st.spinner(t["loading"]):
            text, model, errors = generate_notes(
                plan_md, t, "English" if lang == "EN" else "German", gemini_key
            )
        if text:
            st.session_state.notes[cache_key] = (text, model)
        else:
            st.error(t["all_failed"])
            if errors:
                with st.expander(t["error_details"]):
                    st.code("\n\n".join(errors))

# Output: always the schedule, plus notes if we have them for these exact inputs.
st.markdown(plan_md)

notes = st.session_state.notes.get(cache_key)
full_doc = plan_md
if notes:
    text, model = notes
    st.markdown(f"### {t['h_notes']}")
    st.markdown(text)
    st.caption(t["powered"].format(model=model))
    full_doc += f"\n\n### {t['h_notes']}\n\n{text}"

st.divider()
st.caption(t["tip"])
st.download_button(
    t["download"],
    data=full_doc.encode("utf-8"),
    file_name=f"roast_plan_{cache_key[0]}kg_{cache_key[1].replace(':', '')}_{lang}.md",
    mime="text/markdown",
)