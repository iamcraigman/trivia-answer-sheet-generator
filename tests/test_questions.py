from trivia_kit.models import Round
from trivia_kit.questions import parse_questions, template_csv

ROUNDS = (Round("Geography", questions=2, extra="tiebreaker"), Round("Music", "music", 1))


def parse(text):
    return parse_questions(text, ROUNDS)


def test_rounds_match_by_name_or_position():
    result = parse("round,question,answer\nGeography,Q1,A1\n1,Q2,A2\nmusic,Q3,A3\n2,Q4,A4\n")
    assert [q.answer for q in result.by_round[0]] == ["A1", "A2"]
    assert [q.answer for q in result.by_round[1]] == ["A3", "A4"]


def test_numbers_are_filled_in_and_extras_recognised():
    result = parse("round,number,question,answer\n1,,a,1\n1,,b,2\n1,TB,tie,3\n")
    assert [q.number for q in result.by_round[0]] == ["1", "2", "TB"]
    assert [q.extra for q in result.by_round[0]] == [False, False, True]


def test_spreadsheet_paste_is_tab_separated():
    result = parse("Round\tQuestion\tAnswer\tNotes\nGeography\tCapital of France, right?\tParis\tEasy\n")
    q = result.by_round[0][0]
    assert (q.text, q.answer, q.notes) == ("Capital of France, right?", "Paris", "Easy")


def test_quoted_commas_and_column_aliases():
    result = parse('RD,Q,A\n1,"Who, what, where?",Nobody\n')
    assert result.by_round[0][0].text == "Who, what, where?"


def test_unknown_rounds_are_skipped_with_a_warning():
    result = parse("round,answer\nAtlantis,x\n9,y\n1,ok\n")
    assert len(result.by_round[0]) == 1
    assert sum("no round matches" in w for w in result.warnings) == 2


def test_count_mismatch_warns():
    result = parse("round,answer\n1,only one\n")
    assert any("Geography" in w and "1 question(s)" in w and "set to 2" in w for w in result.warnings)


def test_missing_columns_is_an_error():
    assert parse("foo,bar\n1,2\n").errors
    assert parse("round,notes\n1,x\n").errors


def test_blank_input_and_blank_rows():
    assert not parse("").has_data and not parse("   \n").errors
    assert len(parse("round,answer\n\n1,a\n,,\n").by_round[0]) == 1


def test_byte_order_mark_is_ignored():
    assert parse("﻿round,answer\n1,a\n").has_data


def test_template_matches_the_rounds_and_parses_back():
    text = template_csv(ROUNDS)
    assert text.splitlines()[0] == "round,number,question,answer,notes"
    assert text.count("Geography") == 3 and "Geography,TB" in text
    result = parse(text)
    assert not result.errors and len(result.by_round[0]) == 3
