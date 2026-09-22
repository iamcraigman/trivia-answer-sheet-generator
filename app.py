import dataclasses
import json

import streamlit as st

from trivia_kit.host import generate_answer_key_html, generate_host_script_html, generate_scoresheet_html
from trivia_kit.images import LOGO_MAX_PX, PICTURE_MAX_PX, to_data_uri
from trivia_kit.models import (
    EXTRAS, FORMATS, LAYOUTS, MAX_NAME_LEN, MAX_ROUNDS, MAX_TEAMS, PACKET_ORDERS, PAPERS,
    TEAM_MODES, EventConfig, Round,
)
from trivia_kit.pdf import build_pdf, pdf_to_pngs
from trivia_kit.questions import EXAMPLE_ROUNDS_CSV, import_rounds, parse_questions, template_csv
from trivia_kit.sheets import generate_trivia_html
from trivia_kit.state import mc_options_from_text, state_from_config, state_from_rounds

IMAGE_TYPES = ["png", "jpg", "jpeg", "gif", "webp"]
PREVIEW_PAGES = 3

DEFAULTS = {
    "event_title": "", "event_date": "", "event_venue": "",
    "paper": "Letter", "layout": "4up", "ink_saver": False,
    "team_mode": "blank", "num_teams": 4, "team_names": "", "packet_order": "packets",
    "questions_csv": "", "num_rounds": 5,
}


@st.cache_data(show_spinner=False)
def process_image(data, max_px):
    return to_data_uri(data, max_px)


@st.cache_data(show_spinner="Rendering preview…", max_entries=20)
def render_preview(config_json, round_index):
    config = EventConfig.from_dict(json.loads(config_json))
    pdf, _ = build_pdf(generate_trivia_html(config, only_round=round_index))
    return pdf_to_pngs(pdf, max_pages=1)[0]


def read_images(files, max_px):
    uris = []
    for f in files:
        try:
            uris.append(process_image(f.getvalue(), max_px))
        except ValueError:
            st.warning(f"Skipped '{f.name}': it isn't an image this app can read.")
    return tuple(uris)


def _clear_saved_pictures():
    for key in [k for k in st.session_state if k.startswith("pics_saved_")]:
        del st.session_state[key]


def _decode_upload(upload):
    raw = upload.getvalue()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def load_setup():
    upload = st.session_state.get("setup_upload")
    if upload is None:
        return
    try:
        config = EventConfig.from_dict(json.loads(upload.getvalue()))
    except ValueError as exc:
        st.session_state["setup_error"] = f"That file isn't a usable setup ({exc})."
        return
    st.session_state.pop("setup_error", None)
    _clear_saved_pictures()
    st.session_state.update(state_from_config(config))


def load_questions_file():
    upload = st.session_state.get("csv_upload")
    if upload is not None:
        st.session_state["questions_csv"] = _decode_upload(upload)


def import_rounds_file():
    upload = st.session_state.get("rounds_upload")
    if upload is None:
        return
    text = _decode_upload(upload)
    result = import_rounds(text)
    if result.errors:
        st.session_state["rounds_import_error"] = result.errors[0]
        st.session_state["rounds_import_warnings"] = []
        return
    # Clamp against the layout already chosen in section 1, same as every other
    # source of round data (manual entry, a loaded setup file).
    layout = st.session_state.get("layout", "4up")
    config = EventConfig.from_dict({"layout": layout, "rounds": result.rounds})
    st.session_state.pop("rounds_import_error", None)
    st.session_state["rounds_import_warnings"] = result.warnings
    _clear_saved_pictures()
    st.session_state.update(state_from_rounds(config.rounds))
    st.session_state["num_rounds"] = len(config.rounds)
    # The same file also has the questions and answers section 4 needs; a picture
    # round's images still need adding by hand below, the same as a manually added one.
    st.session_state["questions_csv"] = text


def _resolve_mc_options(rnd, index, parsed):
    """A Choice round's real answer options, one tuple per question: the
    questions file (section 4) takes precedence per question, falling back to
    the round's own compact box for any question the file doesn't cover."""
    if rnd.kind != "choice":
        return rnd
    fallback = mc_options_from_text(st.session_state.get(f"mc_opts_{index}", ""))
    from_file = {}
    for q in parsed.by_round.get(index, []):
        if q.extra or not q.options:
            continue
        try:
            from_file[int(q.number)] = q.options
        except ValueError:
            pass
    if not from_file and not any(fallback):
        return rnd  # no options anywhere; leave mc_options at its current (canonical empty) value
    merged = tuple(
        (from_file.get(n) or (fallback[n - 1] if n - 1 < len(fallback) else ()))[: rnd.choices]
        for n in range(1, rnd.questions + 1)
    )
    return dataclasses.replace(rnd, mc_options=merged)


def compile_documents(config, parsed):
    docs = []

    def add(label, filename, html):
        pdf, pages = build_pdf(html)
        try:
            previews = pdf_to_pngs(pdf, max_pages=PREVIEW_PAGES)
        except ImportError:
            previews = []
        docs.append({"label": label, "filename": filename, "pdf": pdf, "pages": pages, "previews": previews})

    sheets_html = generate_trivia_html(config)
    add("Team answer sheets", "trivia_night_pack.pdf", sheets_html)
    add("Master scoresheet", "trivia_master_scoresheet.pdf", generate_scoresheet_html(config))
    if parsed.has_data:
        add("Answer key", "trivia_answer_key.pdf", generate_answer_key_html(config, parsed.by_round))
        add("Host script", "trivia_host_script.pdf", generate_host_script_html(config, parsed.by_round))
    return {"fingerprint": config.fingerprint(), "docs": docs, "sheets_html": sheets_html}


st.set_page_config(page_title="Trivia Night Kit", layout="centered")
st.title("🎯 Trivia Night Kit")
st.write(
    "Set up your event, then export print-ready team answer sheets, a master scoresheet, "
    "and (if you add your questions) an answer key and host script."
)

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

setup_box = st.expander("💾 Save or load a setup")
with setup_box:
    st.file_uploader("Load a saved setup (.json)", type=["json"], key="setup_upload", on_change=load_setup)
    if st.session_state.get("setup_error"):
        st.error(st.session_state["setup_error"])

# 1. Event
st.subheader("1. Event")
col1, col2, col3 = st.columns(3)
title = col1.text_input("Event name", key="event_title", max_chars=MAX_NAME_LEN, placeholder="Thursday Trivia Night")
date = col2.text_input("Date", key="event_date", max_chars=MAX_NAME_LEN, placeholder="Sep 24")
venue = col3.text_input("Venue", key="event_venue", max_chars=MAX_NAME_LEN, placeholder="The Rusty Anchor")

logo = ""
logo_file = st.file_uploader("Logo (optional, printed in each sheet's header)", type=IMAGE_TYPES, key="logo_upload")
if logo_file:
    processed = read_images([logo_file], LOGO_MAX_PX)
    logo = processed[0] if processed else ""
elif st.session_state.get("logo_saved"):
    logo = st.session_state["logo_saved"]
    st.caption("Using the logo from the loaded setup.")
    if st.button("Remove that logo"):
        st.session_state["logo_saved"] = ""
        st.rerun()

col1, col2, col3 = st.columns([1, 2, 2])
paper = col1.selectbox("Paper", options=list(PAPERS), key="paper")
layout = col2.selectbox("Sheets per page", options=list(LAYOUTS), format_func=lambda k: LAYOUTS[k].label, key="layout")
ink_saver = col3.checkbox("Ink saver (outlined headers instead of solid bars)", key="ink_saver")
max_questions = LAYOUTS[layout].max_questions

# 2. Teams
st.subheader("2. Teams")
team_mode = st.selectbox("Sheet labels", options=list(TEAM_MODES), format_func=TEAM_MODES.get, key="team_mode")
team_names = ()
num_teams = st.session_state["num_teams"]
if team_mode == "tables":
    num_teams = st.number_input("Number of teams", min_value=1, max_value=MAX_TEAMS, key="num_teams")
elif team_mode == "names":
    st.text_area("Team names (one per line)", key="team_names", height=150)
    lines = [ln.strip()[:MAX_NAME_LEN] for ln in st.session_state["team_names"].splitlines() if ln.strip()]
    team_names = tuple(lines[:MAX_TEAMS])
    if len(lines) > MAX_TEAMS:
        st.warning(f"Only the first {MAX_TEAMS} teams are used.")
    if not team_names:
        st.caption("Add at least one team name to get labelled sheets.")
packet_order = st.session_state["packet_order"]
if team_mode == "blank":
    st.caption("Blank template: one page per round, ready to photocopy.")
else:
    packet_order = st.selectbox("Page order", options=list(PACKET_ORDERS), format_func=PACKET_ORDERS.get, key="packet_order")

# 3. Rounds
st.subheader("3. Rounds")
with st.expander("📥 Import rounds from a file (optional)"):
    st.caption(
        "One row per question, like section 4 below, but with extra columns that build the rounds "
        "themselves instead of just answering already-configured ones: **format** (Single Column, "
        "Two Columns (Music), True/False, Multiple Choice, or Picture Round), **points** and **choices**. "
        "A round's question count is however many rows it has. Importing replaces your current rounds "
        "and fills in section 4 with this same file — a picture round's images still need adding below. "
        "For a Multiple Choice round, an **options** column (see section 4) prints the real answer choices."
    )
    st.file_uploader("Upload a CSV, TSV, or spreadsheet export", type=["csv", "tsv", "txt"], key="rounds_upload", on_change=import_rounds_file)
    if st.session_state.get("rounds_import_error"):
        st.error(st.session_state["rounds_import_error"])
    for message in st.session_state.get("rounds_import_warnings", []):
        st.warning(message)
    st.download_button("Download an example file", EXAMPLE_ROUNDS_CSV, "rounds_example.csv", "text/csv")

num_rounds = st.number_input("How many rounds total?", min_value=1, max_value=MAX_ROUNDS, key="num_rounds")

rounds = []
for i in range(int(num_rounds)):
    st.session_state.setdefault(f"name_{i}", f"Round {i+1}")
    st.session_state.setdefault(f"type_{i}", "single")
    st.session_state.setdefault(f"q_{i}", min(10, max_questions))
    st.session_state.setdefault(f"pts_{i}", 1)
    st.session_state.setdefault(f"extra_{i}", "none")
    st.session_state.setdefault(f"choices_{i}", 4)
    st.session_state.setdefault(f"mc_opts_{i}", "")
    st.session_state[f"q_{i}"] = min(st.session_state[f"q_{i}"], max_questions)  # the layout may have shrunk

    with st.container(border=True):
        st.markdown(f"### 📋 Round {i+1}")
        col1, col2, col3 = st.columns([2, 1, 2])
        name = col1.text_input(f"Round {i+1} Name", key=f"name_{i}", max_chars=MAX_NAME_LEN)
        q_count = col2.number_input(f"Questions (1-{max_questions})", min_value=1, max_value=max_questions, key=f"q_{i}")
        kind = col3.selectbox("Answer format", options=list(FORMATS), format_func=FORMATS.get, key=f"type_{i}")

        col1, col2, col3 = st.columns(3)
        points = col1.number_input("Points per question", min_value=1, max_value=99, key=f"pts_{i}")
        extra = col2.selectbox("Extra line", options=list(EXTRAS), format_func=EXTRAS.get, key=f"extra_{i}")
        choices = 4
        if kind == "choice":
            choices = col3.number_input("Choices per question", min_value=2, max_value=6, key=f"choices_{i}")
            st.text_area(
                "Answer options, one line per question (used for any question section 4's file doesn't cover)",
                key=f"mc_opts_{i}", height=100,
                placeholder="Lions, Tigers, Bears, Oh My\nParis, London, Berlin, Madrid",
            )

        images = ()
        if kind == "picture":
            files = st.file_uploader(
                "Pictures, in question order (printed in grayscale)", type=IMAGE_TYPES,
                accept_multiple_files=True, key=f"pics_{i}",
            )
            if files:
                images = read_images(files, PICTURE_MAX_PX)
            elif st.session_state.get(f"pics_saved_{i}"):
                images = tuple(st.session_state[f"pics_saved_{i}"])
                st.caption(f"Using {len(images)} picture(s) from the loaded setup.")
            if images and len(images) != q_count:
                st.caption(
                    f"{len(images)} picture(s) for {q_count} questions: "
                    + ("extra pictures are ignored." if len(images) > q_count else "the remaining frames stay blank.")
                )
            elif not images:
                st.caption("No pictures yet: the sheet will have empty numbered frames.")

    rounds.append(Round(name.strip() or f"Round {i+1}", kind, q_count, points, extra, choices, images))

# 4. Questions
st.subheader("4. Questions and answers (optional)")
st.caption(
    "Add your questions to get an answer key and a host script. Columns: round, number, question, answer, notes, "
    "options. A round is its name or its position (1, 2, ...). Use TB or Bonus as the number for an extra question. "
    "For a Multiple Choice round, **options** prints the real answer choices instead of bare letters — the "
    "choices for that question, comma-separated (e.g. \"Lions, Tigers, Bears, Oh My\"). "
    "(The same file can also build your rounds from scratch — see the importer in section 3 above.)"
)
st.file_uploader("Upload a CSV file", type=["csv", "tsv", "txt"], key="csv_upload", on_change=load_questions_file)
st.text_area("...or paste rows here (a spreadsheet copies as tab-separated text, which works too)", key="questions_csv", height=170)
st.download_button("Download a blank template for these rounds", template_csv(rounds), "questions_template.csv", "text/csv")

parsed = parse_questions(st.session_state["questions_csv"], rounds)
for message in parsed.errors:
    st.error(message)
for message in parsed.warnings:
    st.warning(message)
if parsed.has_data:
    total = sum(len(v) for v in parsed.by_round.values())
    st.caption(f"Read {total} question(s) across {len(parsed.by_round)} round(s).")

rounds = [_resolve_mc_options(r, i, parsed) for i, r in enumerate(rounds)]

config = EventConfig(
    rounds=tuple(rounds), title=title.strip(), date=date.strip(), venue=venue.strip(), logo=logo,
    paper=paper, layout=layout, ink_saver=ink_saver, team_mode=team_mode, num_teams=int(num_teams),
    team_names=team_names, packet_order=packet_order, questions_csv=st.session_state["questions_csv"],
)

with setup_box:
    st.download_button(
        "Save this setup", json.dumps(config.to_dict()), "trivia_setup.json", "application/json",
        help="Includes your rounds, questions, team names, logo and pictures.",
    )

# 5. Preview
st.subheader("5. Preview")
# The browser remembers a selectbox by its displayed label, so the labels must not
# depend on anything the user edits (a round's name) or a rename breaks the selection.
# No key either: changing the number of rounds changes the options, which resets it.
preview_index = st.selectbox("Round to preview", options=range(len(rounds)), format_func=lambda i: f"Round {i + 1}")
st.caption(f"Previewing: {rounds[preview_index].name}")
try:
    preview_config = dataclasses.replace(config, questions_csv="")
    st.image(render_preview(json.dumps(preview_config.to_dict()), preview_index), width="stretch")
except ImportError:
    st.info("Install pypdfium2 (see requirements.txt) to see a live preview here.")

# 6. Export
st.markdown("---")
if st.button("🚀 Compile Trivia Sheets", type="primary"):
    with st.spinner("Building your documents…"):
        # Kept in session state so the download buttons survive the rerun that
        # clicking one of them triggers.
        st.session_state["compiled"] = compile_documents(config, parsed)

compiled = st.session_state.get("compiled")
if compiled:
    if compiled["fingerprint"] != config.fingerprint():
        st.warning("Your setup has changed since the last compile. Compile again to update the downloads.")
    else:
        st.success("Compilation successful!")
        for doc in compiled["docs"]:
            st.download_button(
                f"📥 {doc['label']} (PDF, {doc['pages']} page{'s' if doc['pages'] != 1 else ''})",
                doc["pdf"], doc["filename"], "application/pdf", key=f"dl_{doc['filename']}",
            )
        st.download_button(
            "🌐 Team answer sheets as HTML", compiled["sheets_html"], "trivia_night_template.html", "text/html",
            key="dl_html",
        )
        spec = LAYOUTS[layout]
        if config.teams and config.packet_order == "packets":
            st.info(
                f"Team packets: every {len(rounds)} pages of the team sheets form one group of {spec.per_page} "
                f"team(s). Cut each group along the dashed lines and you get one stack per team, rounds in order."
            )
        with st.expander("👁️ Preview the compiled documents"):
            tabs = st.tabs([d["label"] for d in compiled["docs"]])
            for tab, doc in zip(tabs, compiled["docs"]):
                with tab:
                    for png in doc["previews"]:
                        st.image(png, width="stretch")
                    if doc["pages"] > len(doc["previews"]):
                        st.caption(f"Showing the first {len(doc['previews'])} of {doc['pages']} pages.")
