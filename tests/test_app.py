import json
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

try:
    import trivia_kit.pdf  # noqa: F401
except (ImportError, OSError) as exc:
    pytest.skip(f"WeasyPrint unavailable: {exc}", allow_module_level=True)

from streamlit.testing.v1 import AppTest

from trivia_kit.state import state_from_config
from trivia_kit.models import EventConfig, Round

APP = str(Path(__file__).resolve().parent.parent / "app.py")
DATA_URI = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="


def new_app():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    return at


def click(at, label_part):
    button = next(b for b in at.button if label_part in b.label)
    button.click().run()
    assert not at.exception
    return at


def compiled(at):
    return at.session_state["compiled"]


def test_downloads_survive_a_rerun():
    at = click(new_app(), "Compile")
    assert at.success
    # A download click reruns the script with the compile button unclicked;
    # the results must still be shown.
    at.run()
    assert at.success
    assert [d["filename"] for d in compiled(at)["docs"]] == ["trivia_night_pack.pdf", "trivia_master_scoresheet.pdf"]


def test_editing_anything_flags_stale_downloads():
    at = click(new_app(), "Compile")
    at.text_input(key="name_0").set_value("Changed").run()
    assert at.warning and not at.success
    at.text_input(key="name_0").set_value("Round 1").run()          # back to what was compiled
    assert at.success and not at.warning


def test_blank_round_name_falls_back_to_default():
    at = new_app()
    at.text_input(key="name_2").set_value("   ").run()
    assert "Round 3" in compiled(click(at, "Compile"))["sheets_html"]


def test_pasted_questions_add_an_answer_key_and_host_script():
    at = new_app()
    at.text_area(key="questions_csv").set_value("round,number,question,answer\n1,1,Capital of France?,Paris\n").run()
    assert any("set to 10" in w.value for w in at.warning)          # 1 question in the file, 10 in the round
    docs = compiled(click(at, "Compile"))["docs"]
    assert [d["label"] for d in docs] == ["Team answer sheets", "Master scoresheet", "Answer key", "Host script"]


def test_bad_questions_file_is_reported_not_fatal():
    at = new_app()
    at.text_area(key="questions_csv").set_value("nonsense,columns\n1,2\n").run()
    assert at.error and not at.exception


def test_layout_change_clamps_question_counts():
    at = new_app()
    at.selectbox(key="layout").set_value("1up").run()
    at.number_input(key="q_0").set_value(30).run()
    at.selectbox(key="layout").set_value("4up").run()
    assert not at.exception
    assert at.number_input(key="q_0").value == 10


def preview_box(at):
    return next(s for s in at.selectbox if s.label == "Round to preview")


def test_preview_selector_labels_do_not_depend_on_round_names():
    """A browser remembers a selectbox by its displayed label. Labelling the options with
    round names made the stored selection go stale on a rename and crash the next run
    (this can't be reproduced by AppTest, which re-sends the value every time)."""
    at = new_app()
    assert list(preview_box(at).options) == [f"Round {i}" for i in range(1, 6)]
    at.text_input(key="name_1").set_value("Renamed").run()
    assert list(preview_box(at).options) == [f"Round {i}" for i in range(1, 6)]


def test_preview_selection_survives_renaming_and_removing_rounds():
    at = new_app()
    preview_box(at).set_value(1).run()
    at.text_input(key="name_1").set_value("Renamed").run()
    assert not at.exception
    assert preview_box(at).value == 1
    at.number_input(key="num_rounds").set_value(1).run()              # the selected round no longer exists
    assert not at.exception
    assert preview_box(at).value == 0


def test_teams_and_packet_order_reach_the_output():
    at = new_app()
    at.selectbox(key="team_mode").set_value("names").run()
    at.text_area(key="team_names").set_value("Ants\nBees\n\n  Wasps  ").run()
    result = compiled(click(at, "Compile"))
    assert ">Wasps<" in result["sheets_html"]
    sheets = result["docs"][0]
    assert sheets["pages"] == 5                                     # 3 teams fit on one page per round
    assert any("Team packets" in i.value for i in at.info)


def test_saved_setup_round_trips_through_the_widgets():
    config = EventConfig(
        rounds=(
            Round("Music", "music", 8, 2, "tiebreaker"),
            Round("Pics", "picture", 6, 1, "wager", images=(DATA_URI, DATA_URI)),
            Round("MC", "choice", 5, 3, "none", choices=5),
        ),
        title="Night", date="Sep 24", venue="Pub", logo=DATA_URI, paper="A4", layout="2up", ink_saver=True,
        team_mode="names", num_teams=7, team_names=("Ants", "Bees"), packet_order="rounds",
        questions_csv="round,question,answer\n1,Q,A\n",
    )
    at = AppTest.from_file(APP, default_timeout=120)
    for key, value in state_from_config(config).items():
        at.session_state[key] = value
    at.run()
    assert not at.exception
    assert compiled(click(at, "Compile"))["fingerprint"] == config.fingerprint()


def test_loading_a_setup_file_fills_in_the_form():
    config = EventConfig(
        rounds=(Round("Alpha", "truefalse", 7), Round("Beta", "music", 3, 5)),
        title="Loaded Night", team_mode="tables", num_teams=9, logo=DATA_URI,
    )
    at = new_app()
    at.file_uploader(key="setup_upload").upload("trivia_setup.json", json.dumps(config.to_dict()).encode()).run()
    assert not at.exception and not at.error
    assert at.text_input(key="event_title").value == "Loaded Night"
    assert at.number_input(key="num_rounds").value == 2
    assert at.text_input(key="name_1").value == "Beta"
    assert at.number_input(key="num_teams").value == 9
    assert compiled(click(at, "Compile"))["fingerprint"] == config.fingerprint()


@pytest.mark.parametrize("content", [b"not json", b"[1, 2]", b"\xff\xfe\x00bad"])
def test_a_broken_setup_file_shows_an_error_and_changes_nothing(content):
    at = new_app()
    at.file_uploader(key="setup_upload").upload("bad.json", content).run()
    assert not at.exception
    assert at.error
    assert at.text_input(key="name_0").value == "Round 1"


def test_a_setup_file_cannot_smuggle_in_a_remote_image():
    hostile = {"logo": "http://example.invalid/logo.png", "rounds": [{"name": "R", "kind": "picture", "images": ["file:///C:/Windows/win.ini"]}]}
    at = new_app()
    at.file_uploader(key="setup_upload").upload("x.json", json.dumps(hostile).encode()).run()
    html = compiled(click(at, "Compile"))["sheets_html"]
    assert "example.invalid" not in html and "win.ini" not in html
