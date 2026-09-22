from trivia_kit.host import generate_answer_key_html, generate_host_script_html, generate_scoresheet_html
from trivia_kit.models import EventConfig, Round
from trivia_kit.questions import parse_questions

ROUNDS = (Round("Geo <b>", questions=2, points=2, extra="tiebreaker"), Round("Music", "music", 1))
CSV = "round,number,question,answer,notes\n1,1,Q <i>one</i>,A & B,note <x>\n1,2,Q2,A2,\n1,TB,Guess,54,\n"


def config(**kw):
    return EventConfig(rounds=ROUNDS, title="Night <&>", **kw)


def test_scoresheet_has_a_row_per_team_and_a_column_per_round():
    html = generate_scoresheet_html(config(team_mode="tables", num_teams=3))
    assert html.count('<td class="team">') == 3 and "Table 3" in html
    assert "max 4" in html and "max 1" in html          # questions x points
    assert "Tiebreak" in html
    assert html.count("<td></td>") == 3 * (2 + 1 + 2)    # rounds + tiebreak + total + rank


def test_scoresheet_names_and_blank_template():
    named = generate_scoresheet_html(config(team_mode="names", team_names=("Ants", "Bees")))
    assert ">Ants<" in named and ">Bees<" in named
    assert generate_scoresheet_html(config()).count('<td class="team">') == 15


def test_scoresheet_omits_tiebreak_column_when_unused():
    html = generate_scoresheet_html(EventConfig(rounds=(Round("A"),)))
    assert "Tiebreak" not in html


def test_answer_key_and_script_escape_everything():
    by_round = parse_questions(CSV, ROUNDS).by_round
    for html in (generate_answer_key_html(config(), by_round), generate_host_script_html(config(), by_round)):
        for raw in ("<b>", "<i>", "<x>", "Night <&>"):
            assert raw not in html
        assert "Night &lt;&amp;&gt;" in html


def test_answer_key_lists_answers_and_flags_rounds_without_any():
    html = generate_answer_key_html(config(), parse_questions(CSV, ROUNDS).by_round)
    assert "A &amp; B" in html and ">TB<" in html and "54" in html
    assert "No answers provided." in html                # the Music round


def test_host_script_starts_each_round_on_its_own_page_with_notes():
    html = generate_host_script_html(config(), parse_questions(CSV, ROUNDS).by_round)
    assert html.count('class="script-round"') == 2
    assert "Answer: A &amp; B" in html and "note &lt;x&gt;" in html


def test_host_script_lists_options_for_a_choice_round():
    rounds = (Round("MC", "choice", 1, choices=3),)
    csv = 'round,number,question,answer,options\n1,1,Q,B,"A <opt>,B,C"\n'
    html = generate_host_script_html(EventConfig(rounds=rounds), parse_questions(csv, rounds).by_round)
    assert '<b>A</b> A &lt;opt&gt;' in html and '<b>B</b> B' in html and '<b>C</b> C' in html


def test_host_script_options_are_limited_to_the_rounds_choice_count():
    rounds = (Round("MC", "choice", 1, choices=2),)
    csv = 'round,number,question,answer,options\n1,1,Q,A,"A,B,C,D"\n'
    html = generate_host_script_html(EventConfig(rounds=rounds), parse_questions(csv, rounds).by_round)
    options_block = html.split('<div class="options">')[1].split("</div>")[0]
    assert "<b>A</b> A" in options_block and "<b>B</b> B" in options_block
    assert "C" not in options_block and "D" not in options_block


def test_host_script_has_no_options_block_when_the_round_has_none():
    html = generate_host_script_html(config(), parse_questions(CSV, ROUNDS).by_round)
    assert 'class="options"' not in html
