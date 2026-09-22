"""Data model for a trivia event, with JSON save/load."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

CONFIG_VERSION = 1

MAX_ROUNDS = 10
MAX_TEAMS = 40
MAX_NAME_LEN = 40   # round names, team names, and each event text field
MAX_IMAGES = 20     # pictures per picture round
MAX_MC_OPTIONS = 6  # matches Round.choices' own ceiling
MAX_MC_QUESTIONS = 30  # the largest max_questions across all layouts (1up)

FORMATS = {
    "single": "Single Column",
    "music": "Two Columns (Music)",
    "truefalse": "True / False",
    "choice": "Multiple Choice",
    "picture": "Picture Round",
}
EXTRAS = {
    "none": "None",
    "tiebreaker": "Tiebreaker (closest guess)",
    "wager": "Wager question",
}
PAPERS = {"Letter": (215.9, 279.4), "A4": (210.0, 297.0)}  # width x height, mm
TEAM_MODES = {
    "blank": "Blank template (fill in by hand)",
    "tables": "Numbered tables",
    "names": "Team names",
}
PACKET_ORDERS = {
    "packets": "Team packets (stack, cut once, hand out)",
    "rounds": "By round",
}


@dataclass(frozen=True)
class Layout:
    label: str
    cols: int
    rows: int
    landscape: bool
    max_questions: int
    row_cap: int  # tallest answer row, in px

    @property
    def per_page(self):
        return self.cols * self.rows


LAYOUTS = {
    "4up": Layout("4 per page (2×2, landscape)", 2, 2, True, 10, 24),
    "2up": Layout("2 per page (side by side, landscape)", 2, 1, True, 25, 52),
    "1up": Layout("1 per page (portrait)", 1, 1, False, 30, 64),
}


@dataclass(frozen=True)
class Round:
    name: str
    kind: str = "single"
    questions: int = 10
    points: int = 1
    extra: str = "none"
    choices: int = 4                 # multiple-choice rounds only
    images: tuple[str, ...] = ()     # picture rounds only, as data: URIs
    # multiple-choice rounds only: mc_options[i] holds question (i+1)'s answer
    # choices, up to `choices` of them; () for a question with none yet, which
    # prints as plain lettered circles instead of the real choice text.
    mc_options: tuple[tuple[str, ...], ...] = ()

    @property
    def max_points(self):
        return self.questions * self.points


@dataclass(frozen=True)
class EventConfig:
    rounds: tuple[Round, ...]
    title: str = ""
    date: str = ""
    venue: str = ""
    logo: str = ""                   # data: URI
    paper: str = "Letter"
    layout: str = "4up"
    ink_saver: bool = False
    team_mode: str = "blank"
    num_teams: int = 4
    team_names: tuple[str, ...] = ()
    packet_order: str = "packets"
    questions_csv: str = ""

    @property
    def layout_spec(self):
        return LAYOUTS[self.layout]

    @property
    def teams(self):
        """How many teams get their own pre-labelled sheets (0 = blank template)."""
        if self.team_mode == "tables":
            return self.num_teams
        if self.team_mode == "names":
            return len(self.team_names)
        return 0

    @property
    def event_line(self):
        return " · ".join(p for p in (self.title, self.date, self.venue) if p)

    def to_dict(self):
        return {
            "version": CONFIG_VERSION,
            "title": self.title,
            "date": self.date,
            "venue": self.venue,
            "logo": self.logo,
            "paper": self.paper,
            "layout": self.layout,
            "ink_saver": self.ink_saver,
            "team_mode": self.team_mode,
            "num_teams": self.num_teams,
            "team_names": list(self.team_names),
            "packet_order": self.packet_order,
            "questions_csv": self.questions_csv,
            "rounds": [
                {
                    "name": r.name,
                    "kind": r.kind,
                    "questions": r.questions,
                    "points": r.points,
                    "extra": r.extra,
                    "choices": r.choices,
                    "images": list(r.images),
                    "mc_options": [list(opts) for opts in r.mc_options],
                }
                for r in self.rounds
            ],
        }

    def fingerprint(self):
        """Stable hash of everything that affects the output."""
        blob = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha1(blob).hexdigest()

    @classmethod
    def from_dict(cls, data):
        """Build a config from untrusted data (e.g. a loaded setup file),
        clamping or defaulting anything out of range."""
        if not isinstance(data, dict):
            raise ValueError("A setup file must contain a JSON object.")
        layout = _choice(data.get("layout"), LAYOUTS, "4up")
        max_q = LAYOUTS[layout].max_questions
        raw_rounds = data.get("rounds")
        rounds = tuple(
            _round_from_dict(r, max_q, i)
            for i, r in enumerate(
                r for r in (raw_rounds if isinstance(raw_rounds, list) else [])[:MAX_ROUNDS] if isinstance(r, dict)
            )
        ) or (Round("Round 1", questions=min(10, max_q)),)
        raw_names = data.get("team_names")
        names = tuple(
            n for n in (_text(x, MAX_NAME_LEN) for x in (raw_names if isinstance(raw_names, list) else []))
            if n
        )[:MAX_TEAMS]
        return cls(
            rounds=rounds,
            title=_text(data.get("title"), MAX_NAME_LEN),
            date=_text(data.get("date"), MAX_NAME_LEN),
            venue=_text(data.get("venue"), MAX_NAME_LEN),
            logo=_image(data.get("logo")),
            paper=_choice(data.get("paper"), PAPERS, "Letter"),
            layout=layout,
            ink_saver=bool(data.get("ink_saver", False)),
            team_mode=_choice(data.get("team_mode"), TEAM_MODES, "blank"),
            num_teams=_int(data.get("num_teams"), 1, MAX_TEAMS, 4),
            team_names=names,
            packet_order=_choice(data.get("packet_order"), PACKET_ORDERS, "packets"),
            questions_csv=data.get("questions_csv") if isinstance(data.get("questions_csv"), str) else "",
        )


def _round_from_dict(data, max_questions, index):
    images = data.get("images")
    return Round(
        name=_text(data.get("name"), MAX_NAME_LEN) or f"Round {index + 1}",
        kind=_choice(data.get("kind"), FORMATS, "single"),
        questions=_int(data.get("questions"), 1, max_questions, min(10, max_questions)),
        points=_int(data.get("points"), 1, 99, 1),
        extra=_choice(data.get("extra"), EXTRAS, "none"),
        choices=_int(data.get("choices"), 2, 6, 4),
        images=tuple(
            u for u in (_image(x) for x in (images if isinstance(images, list) else [])) if u
        )[:MAX_IMAGES],
        mc_options=_mc_options(data.get("mc_options")),
    )


def _mc_options(value):
    """A list of per-question option lists, positionally preserved (a question
    with none yet stays `()`, not dropped) so `mc_options[i]` still lines up
    with question i+1 after clamping."""
    if not isinstance(value, list):
        return ()
    result = []
    for entry in value[:MAX_MC_QUESTIONS]:
        if not isinstance(entry, list):
            result.append(())
            continue
        result.append(tuple(o for o in (_text(x, MAX_NAME_LEN) for x in entry[:MAX_MC_OPTIONS]) if o))
    return tuple(result)


def _choice(value, options, default):
    return value if isinstance(value, str) and value in options else default


def _int(value, lo, hi, default):
    if isinstance(value, bool):
        return default
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _text(value, limit):
    return str(value).strip()[:limit] if isinstance(value, (str, int, float)) else ""


def _image(value):
    """Only inline images are accepted: anything else could make the PDF
    renderer fetch a local file or a remote URL."""
    if isinstance(value, str) and value.startswith("data:image/"):
        return value
    return ""
