"""HTML for the host's own documents: master scoresheet, answer key, host script."""
from html import escape

BLANK_SCORESHEET_ROWS = 15

HOST_CSS = """
    *, *::before, *::after { box-sizing: border-box; }
    @page { size: @@PAGE_SIZE@@; margin: 12mm; }
    body { margin: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #000000; }
    h1 { margin: 0 0 2px; font-size: 18pt; }
    .event { margin: 0 0 10px; font-size: 10pt; color: #333333; }
    table { border-collapse: collapse; width: 100%; }
    th { background-color: #1a1a1a; color: #ffffff; font-size: 8pt; text-transform: uppercase; padding: 4px; text-align: center; }
    th .max { display: block; font-weight: normal; text-transform: none; font-size: 7pt; color: #dddddd; }
    td { border: 1px solid #999999; height: 28px; padding: 2px 5px; font-size: 9pt; }
    td.team { font-weight: bold; }
    tr { break-inside: avoid; }
    .key-columns { column-count: 2; column-gap: 10mm; }
    .key-round { break-inside: avoid; margin-bottom: 5mm; border: 1px solid #999999; }
    .key-head { background-color: #1a1a1a; color: #ffffff; padding: 3px 6px; font-size: 9pt; font-weight: bold; text-transform: uppercase; }
    .key-head span { font-weight: normal; text-transform: none; font-size: 7.5pt; color: #dddddd; }
    .key-item { display: table; width: 100%; border-top: 1px solid #cccccc; font-size: 9.5pt; }
    .key-item .n { display: table-cell; width: 34px; padding: 2px 6px; font-weight: bold; text-align: center; background-color: #e5e5e5; }
    .key-item .a { display: table-cell; padding: 2px 6px; }
    .key-empty { padding: 4px 6px; color: #777777; font-size: 9pt; }
    .script-round { break-before: page; }
    .script-round:first-of-type { break-before: auto; }
    .script-round h2 { margin: 0 0 8px; padding: 4px 8px; background-color: #1a1a1a; color: #ffffff; font-size: 13pt; }
    .script-round h2 span { font-weight: normal; font-size: 9pt; color: #dddddd; }
    .q { break-inside: avoid; margin: 0 0 9px; padding-bottom: 7px; border-bottom: 1px solid #cccccc; }
    .q .text { font-size: 12pt; white-space: pre-line; }
    .q .num { display: inline-block; min-width: 24px; padding-right: 6px; font-weight: bold; }
    .q .ans { margin-top: 3px; padding-left: 30px; font-size: 11pt; font-weight: bold; }
    .q .notes { margin-top: 2px; padding-left: 30px; font-size: 9pt; font-style: italic; color: #555555; white-space: pre-line; }
    .missing { color: #777777; font-style: italic; }
"""


def _page(config, title, body, landscape=False):
    size = f"{config.paper.lower()} {'landscape' if landscape else 'portrait'}"
    event = f'<p class="event">{escape(config.event_line)}</p>' if config.event_line else ""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{HOST_CSS.replace("@@PAGE_SIZE@@", size)}</style>
</head>
<body>
<h1>{escape(title)}</h1>
{event}
{body}
</body></html>"""


def _round_meta(rnd):
    return f"{rnd.points} pt{'s' if rnd.points != 1 else ''} each · {rnd.questions} questions"


def generate_scoresheet_html(config):
    """One row per team, one column per round, plus total and rank."""
    if config.team_mode == "tables":
        labels = [f"Table {n}" for n in range(1, config.teams + 1)]
    elif config.team_mode == "names":
        labels = list(config.team_names)
    else:
        labels = [""] * BLANK_SCORESHEET_ROWS

    has_tiebreak = any(r.extra == "tiebreaker" for r in config.rounds)
    heads = "".join(
        f'<th>{escape(r.name)}<span class="max">max {r.max_points}</span></th>' for r in config.rounds
    )
    if has_tiebreak:
        heads += '<th>Tiebreak<span class="max">closest guess</span></th>'
    heads += '<th>Total</th><th>Rank</th>'

    blanks = "<td></td>" * (len(config.rounds) + (1 if has_tiebreak else 0) + 2)
    rows = "".join(f'<tr><td class="team">{escape(label)}</td>{blanks}</tr>' for label in labels)

    body = f"""
<table>
<colgroup><col style="width:24%"></colgroup>
<thead><tr><th style="text-align:left">Team</th>{heads}</tr></thead>
<tbody>{rows}</tbody>
</table>"""
    return _page(config, "Master Scoresheet", body, landscape=True)


def generate_answer_key_html(config, by_round):
    """All answers on as few pages as possible, one box per round."""
    boxes = ""
    for i, rnd in enumerate(config.rounds):
        questions = by_round.get(i, [])
        head = f'<div class="key-head">{escape(rnd.name)} <span>· {_round_meta(rnd)}</span></div>'
        if questions:
            items = "".join(
                f'<div class="key-item"><span class="n">{escape(q.number)}</span>'
                f'<span class="a">{escape(q.answer) or "&mdash;"}</span></div>'
                for q in questions
            )
        else:
            items = '<div class="key-empty">No answers provided.</div>'
        boxes += f'<div class="key-round">{head}{items}</div>'
    return _page(config, "Answer Key", f'<div class="key-columns">{boxes}</div>')


def generate_host_script_html(config, by_round):
    """Every question with its answer and notes, each round starting a new page."""
    sections = ""
    for i, rnd in enumerate(config.rounds):
        questions = by_round.get(i, [])
        if questions:
            items = ""
            for q in questions:
                text = escape(q.text) if q.text else '<span class="missing">(no question text)</span>'
                answer = escape(q.answer) if q.answer else '<span class="missing">(no answer)</span>'
                notes = f'<div class="notes">{escape(q.notes)}</div>' if q.notes else ""
                items += (
                    '<div class="q">'
                    f'<div class="text"><span class="num">{escape(q.number)}.</span>{text}</div>'
                    f'<div class="ans">Answer: {answer}</div>{notes}</div>'
                )
        else:
            items = '<p class="missing">No questions provided for this round.</p>'
        sections += (
            f'<div class="script-round"><h2>{escape(rnd.name)} <span>· {_round_meta(rnd)}</span></h2>{items}</div>'
        )
    return _page(config, "Host Script", sections)
