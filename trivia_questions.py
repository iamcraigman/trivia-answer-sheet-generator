"""Parses the host's questions (CSV, or a pasted spreadsheet) for a set of rounds."""
import csv
import io
from dataclasses import dataclass, field

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
}


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
