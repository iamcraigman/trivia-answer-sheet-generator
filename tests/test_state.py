from trivia_kit.models import EventConfig, Round
from trivia_kit.state import mc_options_from_text, mc_options_to_text, state_from_config, state_from_rounds


def test_state_from_rounds_maps_every_per_round_widget_key():
    rounds = (
        Round("Alpha", "music", 8, 2, "tiebreaker", images=()),
        Round("Beta", "picture", 5, 1, "wager", choices=5, images=("data:image/jpeg;base64,AAAA",)),
    )
    state = state_from_rounds(rounds)
    assert state["name_0"] == "Alpha" and state["type_0"] == "music"
    assert (state["q_0"], state["pts_0"], state["extra_0"]) == (8, 2, "tiebreaker")
    assert state["choices_1"] == 5
    assert state["pics_saved_1"] == ("data:image/jpeg;base64,AAAA",)
    assert state["pics_saved_0"] == ()
    assert state["mc_opts_0"] == state["mc_opts_1"] == ""
    assert set(state) == {
        "name_0", "type_0", "q_0", "pts_0", "extra_0", "choices_0", "pics_saved_0", "mc_opts_0",
        "name_1", "type_1", "q_1", "pts_1", "extra_1", "choices_1", "pics_saved_1", "mc_opts_1",
    }


def test_state_from_rounds_fills_in_the_mc_options_fallback_textarea():
    rnd = Round("Q", "choice", 3, choices=4, mc_options=(("Lions", "Tigers"), (), ("Paris", "London", "Berlin")))
    state = state_from_rounds((rnd,))
    assert state["mc_opts_0"] == "Lions, Tigers\n\nParis, London, Berlin"


def test_mc_options_text_conversion_round_trips():
    options = (("Lions", "Tigers", "Bears", "Oh My"), (), ("Paris",))
    text = mc_options_to_text(options)
    assert text == "Lions, Tigers, Bears, Oh My\n\nParis"
    assert mc_options_from_text(text) == options


def test_mc_options_from_text_ignores_stray_commas_and_whitespace():
    assert mc_options_from_text(" Lions ,, Tigers \n\n") == (("Lions", "Tigers"), ())


def test_state_from_rounds_handles_no_rounds():
    assert state_from_rounds(()) == {}


def test_state_from_config_includes_state_from_rounds_plus_event_level_keys():
    config = EventConfig(
        rounds=(Round("Solo"),), title="Night", team_mode="names", team_names=("Ants", "Bees"),
    )
    state = state_from_config(config)
    assert state["name_0"] == "Solo"                # from state_from_rounds
    assert state["event_title"] == "Night"           # event-level, not touched by state_from_rounds
    assert state["team_names"] == "Ants\nBees"
    assert state["num_rounds"] == 1
