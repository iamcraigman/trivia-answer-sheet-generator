import pytest

from trivia_kit.models import LAYOUTS, MAX_NAME_LEN, EventConfig, Round
from trivia_kit.questions import EXAMPLE_ROUNDS_CSV, import_rounds, parse_questions, template_csv

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


class TestImportRounds:
    """`import_rounds` builds round definitions from a file with no pre-existing
    rounds to match against, unlike `parse_questions` above."""

    def test_infers_name_format_points_choices_and_question_count_in_file_order(self):
        text = (
            "round,format,points,choices,question,answer\n"
            "Movies,Multiple Choice,3,5,Q1,A1\n"
            "Movies,Multiple Choice,3,5,Q2,A2\n"
            "Geography,Single Column,1,,Q1,A1\n"
        )
        result = import_rounds(text)
        assert not result.errors
        assert [r["name"] for r in result.rounds] == ["Movies", "Geography"]  # order of first appearance
        movies, geography = result.rounds
        assert (movies["kind"], movies["points"], movies["choices"], movies["questions"]) == ("choice", "3", "5", 2)
        assert (geography["kind"], geography["points"], geography["questions"]) == ("single", "1", 1)

    def test_needs_no_pre_existing_rounds(self):
        result = import_rounds("round,question,answer\nBrand New Round,Q,A\n")
        assert not result.errors
        assert result.rounds[0]["name"] == "Brand New Round"

    def test_tb_and_bonus_rows_set_the_rounds_extra_line(self):
        result = import_rounds("round,number,answer\nA,TB,54\nB,Bonus,x\nC,1,y\n")
        by_name = {r["name"]: r for r in result.rounds}
        assert by_name["A"]["extra"] == "tiebreaker"
        assert by_name["B"]["extra"] == "wager"
        assert by_name["C"]["extra"] == "none"

    @pytest.mark.parametrize("raw,kind", [
        ("Single Column", "single"), ("single", "single"), ("text", "single"),
        ("Two Columns (Music)", "music"), ("music", "music"), ("Song", "music"),
        ("True / False", "truefalse"), ("truefalse", "truefalse"), ("tf", "truefalse"), ("True-False", "truefalse"),
        ("Multiple Choice", "choice"), ("mc", "choice"),
        ("Picture Round", "picture"), ("photo", "picture"),
    ])
    def test_format_matches_labels_slugs_and_synonyms_case_and_punctuation_insensitively(self, raw, kind):
        result = import_rounds(f"round,format,answer\nR,{raw},x\n")
        assert result.rounds[0]["kind"] == kind

    def test_unrecognized_format_warns_and_defaults_to_single(self):
        result = import_rounds("round,format,answer\nR,Hologram,x\n")
        assert result.rounds[0]["kind"] is None  # EventConfig.from_dict defaults an unresolved kind to "single"
        assert any("Hologram" in w and "R" in w for w in result.warnings)

    def test_conflicting_round_level_fields_warn_and_keep_the_first(self):
        result = import_rounds("round,points,answer\nR,2,x\nR,5,y\n")
        assert result.rounds[0]["points"] == "2"
        assert any("more than one points" in w and "'2'" in w and "'5'" in w for w in result.warnings)

    def test_requires_a_round_column(self):
        assert import_rounds("format,answer\nSingle,x\n").errors

    def test_empty_file_is_an_error(self):
        assert import_rounds("").errors
        assert import_rounds("   \n").errors

    def test_a_header_with_no_data_rows_is_an_error(self):
        result = import_rounds("round,answer\n")
        assert result.errors and not result.rounds

    def test_blank_rows_and_byte_order_mark_are_ignored(self):
        result = import_rounds("﻿round,answer\nR,x\n\n,,\n")
        assert not result.errors
        assert result.rounds[0]["questions"] == 1

    def test_result_feeds_directly_into_eventconfig_clamping(self):
        text = "round,format,points,choices,answer\nR,Multiple Choice,999,999,x\n"
        result = import_rounds(text)
        config = EventConfig.from_dict({"layout": "4up", "rounds": result.rounds})
        rnd = config.rounds[0]
        assert rnd.kind == "choice"
        assert rnd.points == 99          # models.py's own points ceiling
        assert rnd.choices == 6          # models.py's own choices ceiling

    def test_question_count_is_clamped_to_the_chosen_layouts_maximum(self):
        text = "round,answer\n" + "\n".join(f"R,{i}" for i in range(40))
        result = import_rounds(text)
        assert result.rounds[0]["questions"] == 40
        config = EventConfig.from_dict({"layout": "4up", "rounds": result.rounds})
        assert config.rounds[0].questions == LAYOUTS["4up"].max_questions

    def test_a_round_name_longer_than_the_limit_is_truncated_like_any_other_source(self):
        long_name = "R" * (MAX_NAME_LEN + 20)
        result = import_rounds(f"round,answer\n{long_name},x\n")
        config = EventConfig.from_dict({"rounds": result.rounds})
        assert len(config.rounds[0].name) == MAX_NAME_LEN

    def test_imported_rounds_can_be_reparsed_by_parse_questions_for_the_same_answers(self):
        """The whole point: app.py reuses the uploaded text as-is for section 4's
        answer key / host script parsing once the imported rounds exist for real."""
        text = (
            "round,format,points,number,question,answer,notes\n"
            "Movies,Multiple Choice,2,1,Which film won Best Picture?,Parasite,2020\n"
            "Movies,Multiple Choice,2,2,Which film won in 2019?,Green Book,\n"
            "Sound,Two Columns (Music),1,1,Clip 1,Bohemian Rhapsody - Queen,\n"
        )
        import_result = import_rounds(text)
        config = EventConfig.from_dict({"rounds": import_result.rounds})
        parsed = parse_questions(text, config.rounds)
        assert not parsed.warnings and not parsed.errors
        assert [q.answer for q in parsed.by_round[0]] == ["Parasite", "Green Book"]
        assert parsed.by_round[1][0].answer == "Bohemian Rhapsody - Queen"

    def test_example_rounds_csv_imports_cleanly_and_reparses_with_no_warnings(self):
        import_result = import_rounds(EXAMPLE_ROUNDS_CSV)
        assert not import_result.errors and not import_result.warnings
        assert [r["name"] for r in import_result.rounds] == ["General Knowledge", "Name That Tune", "Movie Trivia"]
        config = EventConfig.from_dict({"rounds": import_result.rounds})
        assert [r.kind for r in config.rounds] == ["single", "music", "choice"]
        assert config.rounds[0].extra == "tiebreaker"
        parsed = parse_questions(EXAMPLE_ROUNDS_CSV, config.rounds)
        assert not parsed.warnings and not parsed.errors and parsed.has_data
