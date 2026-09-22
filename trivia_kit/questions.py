"""Parses the host's questions (CSV, or a pasted spreadsheet) for a set of rounds."""
import csv
import io
import re
from dataclasses import dataclass, field

from .models import FORMATS

# Values of the `number` column that mark the round's tiebreaker / bonus question.
EXTRA_LABELS = {
    "tb": "TB",
    "tiebreaker": "TB",
    "tie-breaker": "TB",
    "bonus": "Bonus",
    "wager": "Bonus",
}

COLUMN_ALIASES = {
    "round": {"round", "rd"},
    "number": {"number", "no", "num", "#", "q#"},
    "question": {"question", "q", "clue", "prompt"},
    "answer": {"answer", "a", "ans"},
    "notes": {"notes", "note", "comment", "comments"},
    "format": {"format", "type", "kind", "answer format", "answer type"},
    "points": {"points", "pts", "point", "points each", "pts each"},
    "choices": {"choices", "option", "options", "num choices"},
}

# Recognized beyond FORMATS' own keys ("single", "music", ...) and display
# labels ("Single Column", ...), which `_resolve_format` already matches.
FORMAT_SYNONYMS = {
    "tf": "truefalse", "true false": "truefalse", "true or false": "truefalse",
    "mc": "choice", "multi choice": "choice", "multichoice": "choice",
    "song": "music", "songs": "music",
    "image": "picture", "images": "picture", "photo": "picture", "photos": "picture",
    "text": "single", "standard": "single", "basic": "single",
}


def _normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.strip().lower()).strip()


def _resolve_format(raw):
    """Match `raw` against FORMATS' keys/labels or FORMAT_SYNONYMS, ignoring
    case and punctuation. Returns None if nothing matches."""
    key = _normalize(raw)
    if not key:
        return None
    if key in FORMATS:
        return key
    for slug, label in FORMATS.items():
        if key == _normalize(label):
            return slug
    return FORMAT_SYNONYMS.get(key)


@dataclass(frozen=True)
class Question:
    number: str       # "1", "2", ... or "TB" / "Bonus"
    text: str
    answer: str
    notes: str = ""
    extra: bool = False


@dataclass
class ParseResult:
    by_round: dict = field(default_factory=dict)   # round index -> [Question]
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def has_data(self):
        return any(self.by_round.values())


def parse_questions(text, rounds):
    """Match the rows of `text` to `rounds` (a sequence of Round).

    A row's `round` cell is either a round's name or its 1-based position.
    Rows that don't match any round are skipped with a warning.
    """
    result = ParseResult()
    text = text.lstrip("﻿")
    if not text.strip():
        return result

    first_line = text.splitlines()[0]
    delimiter = "\t" if "\t" in first_line and "," not in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader)
    columns = {}
    for i, raw in enumerate(header):
        name = raw.strip().lower()
        for canonical, aliases in COLUMN_ALIASES.items():
            if name in aliases and canonical not in columns:
                columns[canonical] = i
    if "round" not in columns or not ({"question", "answer"} & columns.keys()):
        result.errors.append(
            "The first row must name the columns. It needs a 'round' column and a "
            "'question' and/or 'answer' column (optional: 'number', 'notes')."
        )
        return result

    def cell(row, name):
        i = columns.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    names = {r.name.strip().lower(): i for i, r in enumerate(rounds)}
    counters = {}
    for row in reader:
        if not any(c.strip() for c in row):
            continue
        round_ref = cell(row, "round")
        index = names.get(round_ref.lower())
        if index is None and round_ref.isdigit() and 1 <= int(round_ref) <= len(rounds):
            index = int(round_ref) - 1
        if index is None:
            result.warnings.append(f"Line {reader.line_num}: no round matches '{round_ref}', so it was skipped.")
            continue

        number = cell(row, "number")
        extra_label = EXTRA_LABELS.get(number.lower())
        if not extra_label:
            counters[index] = counters.get(index, 0) + 1
            number = number or str(counters[index])
        result.by_round.setdefault(index, []).append(
            Question(
                number=extra_label or number,
                text=cell(row, "question"),
                answer=cell(row, "answer"),
                notes=cell(row, "notes"),
                extra=bool(extra_label),
            )
        )

    for index, questions in sorted(result.by_round.items()):
        regular = sum(1 for q in questions if not q.extra)
        if regular != rounds[index].questions:
            result.warnings.append(
                f"'{rounds[index].name}' has {regular} question(s) in the file but is set to {rounds[index].questions}."
            )
    return result


@dataclass
class _RoundAccumulator:
    questions: int = 0
    extra: str = "none"
    format: str | None = None
    points: str | None = None
    choices: str | None = None


@dataclass
class RoundsImportResult:
    rounds: list = field(default_factory=list)   # plain dicts, for EventConfig.from_dict({"rounds": ...})
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def import_rounds(text):
    """Infer whole round definitions from `text`: each round's name, answer format,
    points, choices, and whether it has a tiebreaker/wager line, all in order of
    first appearance. This is the same file shape as `parse_questions` (plus a
    few optional columns), so the questions and answers in it can also be read
    with `parse_questions(text, result.rounds)` once those rounds exist for real.

    Unlike `parse_questions`, this needs no pre-existing rounds to match against
    — it's how a whole event can be set up from one file. `result.rounds` is a
    list of plain dicts, not yet validated or clamped; pass them to
    `EventConfig.from_dict({"rounds": result.rounds, ...})`, which does that.
    """
    result = RoundsImportResult()
    text = text.lstrip("﻿")
    if not text.strip():
        result.errors.append("That file is empty.")
        return result

    first_line = text.splitlines()[0]
    delimiter = "\t" if "\t" in first_line and "," not in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader)
    columns = {}
    for i, raw in enumerate(header):
        name = raw.strip().lower()
        for canonical, aliases in COLUMN_ALIASES.items():
            if name in aliases and canonical not in columns:
                columns[canonical] = i
    if "round" not in columns:
        result.errors.append("The first row must name the columns, including a 'round' column.")
        return result

    def cell(row, name):
        i = columns.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    order = []
    accumulated = {}
    for row in reader:
        if not any(c.strip() for c in row):
            continue
        name = cell(row, "round")
        if not name:
            continue
        if name not in accumulated:
            order.append(name)
            accumulated[name] = _RoundAccumulator()
        info = accumulated[name]

        extra_label = EXTRA_LABELS.get(cell(row, "number").lower())
        if extra_label:
            info.extra = "tiebreaker" if extra_label == "TB" else "wager"
        else:
            info.questions += 1

        for attr in ("format", "points", "choices"):
            value = cell(row, attr)
            if not value:
                continue
            current = getattr(info, attr)
            if current is None:
                setattr(info, attr, value)
            elif current != value:
                result.warnings.append(
                    f"'{name}' has more than one {attr} in the file ('{current}' and '{value}'); using '{current}'."
                )

    for name in order:
        info = accumulated[name]
        kind = _resolve_format(info.format) if info.format else None
        if info.format and kind is None:
            result.warnings.append(f"'{name}': unrecognized format '{info.format}', using Single Column.")
        result.rounds.append({
            "name": name, "kind": kind, "questions": info.questions,
            "points": info.points, "choices": info.choices, "extra": info.extra,
        })
    if not result.rounds:
        result.errors.append("No rows had a value in the 'round' column.")
    return result


EXAMPLE_ROUNDS_CSV = """\
round,format,points,number,question,answer,notes
General Knowledge,Single Column,1,1,What is the capital of France?,Paris,
General Knowledge,Single Column,1,2,Who wrote Hamlet?,William Shakespeare,
General Knowledge,Single Column,1,TB,How many countries are in Africa?,54,Closest guess wins
Name That Tune,Two Columns (Music),2,1,Play clip 1,Bohemian Rhapsody - Queen,
Name That Tune,Two Columns (Music),2,2,Play clip 2,Thriller - Michael Jackson,
Movie Trivia,Multiple Choice,1,1,Which film won Best Picture in 2020?,Parasite,
"""


def template_csv(rounds):
    """A ready-to-fill CSV with one blank row per configured question."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["round", "number", "question", "answer", "notes"])
    for rnd in rounds:
        for n in range(1, rnd.questions + 1):
            writer.writerow([rnd.name, n, "", "", ""])
        if rnd.extra != "none":
            writer.writerow([rnd.name, "TB" if rnd.extra == "tiebreaker" else "Bonus", "", "", ""])
    return out.getvalue()
