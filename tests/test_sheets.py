import pytest

from trivia_kit.sheets import generate_trivia_html, page_plan, row_height
from trivia_kit.models import EventConfig, Round


def cfg(*rounds, **kw):
    return EventConfig(rounds=rounds or (Round("R"),), **kw)


def test_text_fields_are_escaped():
    html = generate_trivia_html(cfg(
        Round("<b>Q&A</b> <script>x</script>"),
        title="<i>Night</i>", venue="A & B", team_mode="names", team_names=("<u>Team</u>",),
    ))
    for raw in ("<script>x</script>", "<b>Q&A</b>", "<i>Night</i>", "<u>Team</u>"):
        assert raw not in html
    assert "&lt;b&gt;Q&amp;A&lt;/b&gt;" in html
    assert "A &amp; B" in html


def test_blank_template_is_one_page_per_round_with_identical_sheets():
    config = cfg(Round("A"), Round("B", "music"), Round("C"))
    html = generate_trivia_html(config)
    assert html.count('class="master-grid"') == 3
    assert html.count('class="grid-cell"') == 12


@pytest.mark.parametrize("layout,sheets", [("4up", 4), ("2up", 2), ("1up", 1)])
def test_sheets_per_page_follow_the_layout(layout, sheets):
    html = generate_trivia_html(cfg(Round("A"), layout=layout))
    assert html.count('class="grid-cell"') == sheets


def test_format_specific_columns():
    def html(kind, **kw):
        return generate_trivia_html(cfg(Round("R", kind, **kw)))
    assert "Song Name" in html("music") and "Artist" in html("music")
    assert "Your Answer" in html("single")
    assert html("truefalse").count('class="mark"') == 4 * 10 * 2
    assert html("choice", choices=5).count('class="mark"') == 4 * 10 * 5


def test_numbered_rows_match_question_count_and_sheets_stay_uniform():
    html = generate_trivia_html(cfg(Round("R", questions=4)))
    assert html.count('<td class="q-num">') == 4 * 10       # 10 rows on each of 4 sheets
    assert html.count('<td class="q-num">&nbsp;</td>') == 4 * 6


def test_rows_grow_to_the_longest_round_and_the_layout_maximum():
    html = generate_trivia_html(cfg(Round("R", questions=25), layout="2up"))
    assert html.count('<td class="q-num">') == 2 * 25


def test_extra_lines_and_points():
    html = generate_trivia_html(cfg(Round("T", extra="tiebreaker", points=2, questions=5)))
    assert "closest guess wins" in html
    assert "2 pts each" in html
    assert "/ 10</div>" in html     # max score = questions x points
    assert "wager-box" in generate_trivia_html(cfg(Round("W", extra="wager")))


def test_team_labels():
    tables = generate_trivia_html(cfg(Round("A"), team_mode="tables", num_teams=2))
    assert "Table 1" in tables and "Table 2" in tables and "Table 3" not in tables
    names = generate_trivia_html(cfg(Round("A"), team_mode="names", team_names=("Ants", "Bees")))
    assert ">Ants<" in names and ">Bees<" in names


def test_ink_saver_swaps_the_solid_header_bars_for_outlines():
    outlined = ".header { background-color: #ffffff; color: #000000; border: 2px solid #000000; }"
    normal = generate_trivia_html(cfg(Round("A")))
    saver = generate_trivia_html(cfg(Round("A"), ink_saver=True))
    assert outlined in saver and outlined not in normal
    assert saver.count('class="grid-cell"') == normal.count('class="grid-cell"')


def test_paper_and_orientation_reach_the_page_rule():
    assert "size: a4 landscape" in generate_trivia_html(cfg(Round("A"), paper="A4"))
    assert "size: letter portrait" in generate_trivia_html(cfg(Round("A"), layout="1up"))


def test_rows_are_capped_and_never_below_the_minimum():
    assert row_height(cfg(Round("A")), 10) == 24                       # the original 4-up row height
    assert row_height(cfg(Round("A"), layout="1up"), 10) == 64
    assert row_height(cfg(Round("A")), 200) == 18


class TestPagePlan:
    def config(self, order, teams=6, rounds=3):
        return cfg(*[Round(f"R{i}") for i in range(rounds)], team_mode="tables", num_teams=teams, packet_order=order)

    def test_team_packet_order_groups_a_page_stack_per_set_of_teams(self):
        plan = page_plan(self.config("packets"))
        assert [r for r, _ in plan] == [0, 1, 2, 0, 1, 2]
        assert plan[0][1] == [0, 1, 2, 3] and plan[3][1] == [4, 5, None, None]

    def test_round_order(self):
        assert [r for r, _ in page_plan(self.config("rounds"))] == [0, 0, 1, 1, 2, 2]

    def test_every_team_gets_a_sheet_for_every_round(self):
        for order in ("packets", "rounds"):
            seen = {(r, t) for r, teams in page_plan(self.config(order)) for t in teams if t is not None}
            assert seen == {(r, t) for r in range(3) for t in range(6)}

    def test_blank_template_ignores_order_and_team_count(self):
        config = cfg(Round("A"), Round("B"), team_mode="blank", num_teams=30)
        assert page_plan(config) == [(0, [None] * 4), (1, [None] * 4)]

    def test_only_round_gives_that_rounds_first_page(self):
        assert page_plan(self.config("packets"), only_round=1) == [(1, [0, 1, 2, 3])]
