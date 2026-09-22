import pytest

from trivia_kit.sheets import _mc_option_budget, generate_trivia_html, page_plan, row_height
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


class TestChoiceOptions:
    def test_real_options_print_letter_and_text_instead_of_bare_circles(self):
        rnd = Round("Q", "choice", 2, choices=4, mc_options=(("Lions", "Tigers", "Bears", "Oh My"), ()))
        html = generate_trivia_html(cfg(rnd))
        assert '<b>A</b> Lions' in html and '<b>D</b> Oh My' in html
        assert html.count('class="q-ans q-choices"') == 4     # one per sheet on the 4-up layout

    def test_a_question_without_options_falls_back_to_bare_circles(self):
        rnd = Round("Q", "choice", 2, choices=4, mc_options=(("Lions", "Tigers", "Bears", "Oh My"), ()))
        html = generate_trivia_html(cfg(rnd))
        assert html.count('class="mark"') == 4 * 4        # question 2, on each of the 4 sheets, 4 bare letters

    def test_no_mc_options_at_all_is_unchanged_from_before_the_feature(self):
        html = generate_trivia_html(cfg(Round("Q", "choice", 3, choices=5)))
        assert 'class="q-ans q-choices"' not in html
        assert 'class="q-ans q-marks q-left"' not in html      # stays centered, matching pre-feature rendering
        assert html.count('class="mark"') == 4 * 3 * 5

    def test_a_gap_rows_bare_circles_left_align_when_siblings_have_real_options(self):
        rnd = Round("Q", "choice", 2, choices=4, mc_options=(("Lions", "Tigers", "Bears", "Oh My"), ()))
        html = generate_trivia_html(cfg(rnd))
        assert html.count('class="q-ans q-marks q-left"') == 4     # question 2's gap row, on each of the 4 sheets

    def test_options_beyond_the_rounds_choice_count_are_ignored(self):
        rnd = Round("Q", "choice", 1, choices=2, mc_options=(("Lions", "Tigers", "Bears"),))
        html = generate_trivia_html(cfg(rnd))
        assert '<b>A</b> Lions' in html and '<b>B</b> Tigers' in html
        assert "Bears" not in html

    def test_option_text_is_escaped(self):
        rnd = Round("Q", "choice", 1, mc_options=(("<script>x</script>", "safe"),))
        html = generate_trivia_html(cfg(rnd))
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;" in html

    def test_a_long_option_is_truncated_rather_than_left_to_overflow(self):
        long_option = "A Very Long Answer Choice That Will Not Fit On One Line Of A Printed Row"
        rnd = Round("Q", "choice", 1, choices=4, mc_options=((long_option, "short"),))
        html = generate_trivia_html(cfg(rnd))
        assert long_option not in html
        assert "…" in html

    def test_mc_option_budget_shrinks_as_more_choices_share_the_row(self):
        config = cfg(Round("Q", "choice"))
        few = _mc_option_budget(config, Round("Q", "choice", choices=2))
        many = _mc_option_budget(config, Round("Q", "choice", choices=6))
        assert few > many > 0

    def test_mc_option_budget_is_never_negative_even_on_the_tightest_layout(self):
        config = cfg(Round("Q", "choice"), layout="4up")
        assert _mc_option_budget(config, Round("Q", "choice", choices=6)) >= 4


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
