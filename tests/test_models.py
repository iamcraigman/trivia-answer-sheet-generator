import json

import pytest

from trivia_kit.models import LAYOUTS, MAX_MC_OPTIONS, MAX_MC_QUESTIONS, MAX_NAME_LEN, MAX_ROUNDS, MAX_TEAMS, EventConfig, Round

DATA_URI = "data:image/jpeg;base64,AAAA"


def sample():
    return EventConfig(
        rounds=(
            Round("Music", "music", 8, 2, "tiebreaker"),
            Round("Pics", "picture", 6, 1, "wager", images=(DATA_URI, DATA_URI)),
            Round("MC", "choice", 5, 3, "none", choices=5, mc_options=(
                ("Lions", "Tigers", "Bears", "Oh My"), (), ("Paris", "London"), (), ()
            )),
        ),
        title="Night", date="Sep 24", venue="Pub", logo=DATA_URI, paper="A4", layout="2up", ink_saver=True,
        team_mode="names", num_teams=7, team_names=("Ants", "Bees"), packet_order="rounds",
        questions_csv="round,answer\n1,x\n",
    )


def test_json_round_trip_is_lossless():
    config = sample()
    again = EventConfig.from_dict(json.loads(json.dumps(config.to_dict())))
    assert again == config
    assert again.fingerprint() == config.fingerprint()


def test_fingerprint_changes_with_any_setting():
    base = sample()
    assert base.fingerprint() != EventConfig.from_dict({**base.to_dict(), "venue": "Elsewhere"}).fingerprint()
    assert base.fingerprint() != EventConfig.from_dict({**base.to_dict(), "questions_csv": ""}).fingerprint()


def test_out_of_range_values_are_clamped_or_defaulted():
    config = EventConfig.from_dict({
        "layout": "nope", "paper": "Legal", "team_mode": 5, "num_teams": 9999, "packet_order": None,
        "rounds": [{"name": "  ", "kind": "hologram", "questions": 500, "points": -3, "extra": "?", "choices": 99}],
    })
    rnd = config.rounds[0]
    assert (config.layout, config.paper, config.team_mode, config.packet_order) == ("4up", "Letter", "blank", "packets")
    assert config.num_teams == MAX_TEAMS
    assert rnd.name == "Round 1"
    assert (rnd.kind, rnd.extra) == ("single", "none")
    assert rnd.questions == LAYOUTS["4up"].max_questions
    assert (rnd.points, rnd.choices) == (1, 6)


def test_limits_on_counts_and_lengths():
    config = EventConfig.from_dict({
        "title": "x" * 500,
        "rounds": [{"name": "y" * 500}] * (MAX_ROUNDS + 5),
        "team_names": ["t" * 500] * (MAX_TEAMS + 5) + ["", "  "],
    })
    assert len(config.rounds) == MAX_ROUNDS
    assert len(config.title) == len(config.rounds[0].name) == MAX_NAME_LEN
    assert len(config.team_names) == MAX_TEAMS


def test_a_layout_change_shrinks_the_question_limit():
    config = EventConfig.from_dict({"layout": "4up", "rounds": [{"questions": 25}]})
    assert config.rounds[0].questions == 10


@pytest.mark.parametrize("bad", [None, [], "text", 3, {"rounds": "nope"}, {"rounds": [1, "x", None]}])
def test_junk_never_crashes_and_always_leaves_a_round(bad):
    try:
        config = EventConfig.from_dict(bad)
    except ValueError:
        assert not isinstance(bad, dict)
    else:
        assert len(config.rounds) >= 1


@pytest.mark.parametrize("url", [
    "file:///C:/Windows/win.ini", "http://example.com/x.png", "https://example.com/x.png",
    "/etc/passwd", "javascript:alert(1)", "data:text/html,<script>", "",
])
def test_only_inline_images_are_accepted(url):
    config = EventConfig.from_dict({"logo": url, "rounds": [{"name": "R", "kind": "picture", "images": [url, DATA_URI]}]})
    assert config.logo == ""
    assert config.rounds[0].images == (DATA_URI,)


class TestMcOptions:
    def round_with(self, mc_options):
        return EventConfig.from_dict({"rounds": [{"name": "R", "kind": "choice", "mc_options": mc_options}]}).rounds[0]

    def test_positions_are_preserved_so_gaps_still_line_up_with_the_right_question(self):
        rnd = self.round_with([["Lions", "Tigers"], [], ["Paris"]])
        assert rnd.mc_options == (("Lions", "Tigers"), (), ("Paris",))

    def test_each_option_is_text_stripped_and_length_capped(self):
        rnd = self.round_with([["  Lions  ", "x" * 500, 3, None]])
        options = rnd.mc_options[0]
        assert options[0] == "Lions"
        assert len(options[1]) == MAX_NAME_LEN
        assert options[2] == "3"          # a plain number is coerced to text like other fields, e.g. a round name
        assert len(options) == 3          # None isn't usable text (unlike str/int/float), so it's dropped

    def test_options_per_question_are_capped(self):
        rnd = self.round_with([[f"opt{i}" for i in range(20)]])
        assert len(rnd.mc_options[0]) == MAX_MC_OPTIONS

    def test_number_of_questions_with_options_is_capped(self):
        rnd = self.round_with([["A"]] * (MAX_MC_QUESTIONS + 10))
        assert len(rnd.mc_options) == MAX_MC_QUESTIONS

    @pytest.mark.parametrize("junk", [None, "text", 3, {"a": 1}, [1, "x", None, ["ok"]]])
    def test_junk_never_crashes_and_falls_back_to_no_options(self, junk):
        rnd = self.round_with(junk)
        assert isinstance(rnd.mc_options, tuple)

    def test_default_round_has_no_options(self):
        assert EventConfig.from_dict({"rounds": [{"name": "R"}]}).rounds[0].mc_options == ()
