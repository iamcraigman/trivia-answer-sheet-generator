"""Builds the print-ready HTML for the team answer sheets."""
from html import escape

from .models import PAPERS

MARGIN_MM = 4
MM_TO_PX = 96 / 25.4
MIN_ROWS = 10          # sheets always show at least this many rows, so packets stay uniform
OVERHEAD_PX = 150      # header, team line and column heads, with room for a wrapped round name
MIN_ROW_PX = 18
THEAD_PX = 18          # height of a table's column-head row
SHEET_PADDING_PX = 32     # a cell's side padding and border
TEAM_LINE_FIXED_PX = 185 # the "Team:" and score items that share the line with the name
SUBLINE_MAX = 70       # the small event line under a round's name is cut off here

BASE_CSS = """
    *, *::before, *::after { box-sizing: border-box; }
    @page { size: @@PAGE_SIZE@@; margin: @@MARGIN@@mm; background-color: #ffffff; }
    body { margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #000000; background-color: #ffffff; }
    .master-grid { width: 100%; max-width: 100%; height: 100vh; border-collapse: collapse; break-after: page; table-layout: fixed; }
    .master-grid:last-child { break-after: avoid; }
    .grid-cell { width: @@CELL_W@@%; height: @@CELL_H@@%; vertical-align: top; background-color: #ffffff; border: 2px dashed #777777; padding: 12px 14px; overflow: hidden; position: relative; }
    .grid-cell::before, .grid-cell::after { content: ""; position: absolute; width: 10px; height: 10px; border-color: #555555; }
    .grid-cell::before { top: 2px; left: 2px; border-top: 1.5px solid #555555; border-left: 1.5px solid #555555; }
    .grid-cell::after { bottom: 2px; right: 2px; border-bottom: 1.5px solid #555555; border-right: 1.5px solid #555555; }
    .sheet-wrapper { width: 100%; height: 100%; }
    .header { position: relative; background-color: #333333; color: #ffffff; padding: 5px; border-radius: 4px; border-bottom: 2px solid #000000; text-align: center; margin-bottom: 6px; }
    .header.has-logo { padding-left: 40px; padding-right: 40px; }
    .header .logo { position: absolute; left: 6px; top: 3px; height: 22px; max-width: 30px; background-color: #ffffff; padding: 1px; border-radius: 2px; }
    .header h1 { margin: 0; font-size: 11pt; text-transform: uppercase; letter-spacing: 1px; overflow-wrap: break-word; max-height: 2.3em; overflow: hidden; }
    .header .subline { font-size: 7pt; color: #dddddd; margin-top: 1px; letter-spacing: 0.3px; white-space: nowrap; height: 1.2em; overflow: hidden; }
    .team-info-box { width: 100%; font-size: 8.5pt; display: table; margin-bottom: 6px; }
    .team-info-cell { display: table-cell; vertical-align: middle; white-space: nowrap; }
    .team-info-cell.badge { border: 1.5px solid #000000; border-radius: 3px; padding: 1px 6px; font-weight: bold; }
    .team-info-cell.label { font-weight: bold; color: #000000; padding: 0 4px 0 6px; }
    .team-info-cell.line { width: 100%; border-bottom: 1px dashed #333333; padding: 0 4px; font-weight: bold; font-size: 8pt; }
    .team-info-cell.line .name { overflow: hidden; height: 1.3em; }
    .team-info-cell.score-label { font-weight: bold; color: #000000; text-align: right; padding: 0 5px 0 8px; }
    .team-info-cell.score-box { padding: 0; }
    .score-box span { display: inline-block; width: 36px; height: 18px; border: 2px solid #000000; border-radius: 3px; vertical-align: middle; background-color: white; }
    .team-info-cell.score-max { padding-left: 4px; color: #333333; }
    .answer-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .answer-table th { background-color: #1a1a1a; color: white; padding: 3px 5px; font-size: 8pt; text-transform: uppercase; text-align: left; }
    .answer-table th.num-col { width: 12%; text-align: center; }
    .answer-table th.music-col { width: 44%; }
    .answer-row { break-inside: avoid; }
    .answer-row td { padding: 3px 5px; font-size: 8.5pt; border-bottom: 1px solid #cccccc; line-height: 1.2; vertical-align: middle; }
    .answer-row td.q-num { font-weight: bold; color: #000000; text-align: center; background-color: #e5e5e5; border-right: 1px solid #cccccc; border-left: 1px solid #cccccc; }
    .answer-row td.q-ans, .answer-row td.q-music { border-right: 1px solid #cccccc; background-color: #ffffff; }
    .answer-row td.q-marks { text-align: center; }
    .mark { display: inline-block; border: 1px solid #333333; border-radius: 50%; text-align: center; font-size: 7.5pt; font-weight: bold; margin: 0 9px; }
    .answer-row td.q-choices { font-size: 7.5pt; white-space: nowrap; overflow: hidden; }
    .answer-row td.q-marks.q-left { text-align: left; padding-left: 10px; }
    .q-choices .choice { display: inline-block; margin-right: 8px; }
    .q-choices .choice b { margin-right: 2px; }
    .answer-row td.q-extra { text-align: right; color: #555555; font-size: 7pt; }
    .wager-box { display: inline-block; width: 34px; height: 13px; border: 1.5px solid #000000; border-radius: 2px; vertical-align: middle; margin-left: 4px; }
    .pic-grid { width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 4px; margin: -4px; }
    .pic-cell { vertical-align: top; padding: 0; }
    .pic-frame { position: relative; border: 1px solid #999999; background-color: #ffffff; }
    .pic-frame img { display: block; width: 100%; object-fit: contain; }
    .pic-num { position: absolute; top: 0; left: 0; background-color: #333333; color: #ffffff; font-size: 7pt; font-weight: bold; padding: 0 4px; }
    .pic-line { height: 18px; border-bottom: 1px solid #777777; }
"""

INK_SAVER_CSS = """
    .header { background-color: #ffffff; color: #000000; border: 2px solid #000000; }
    .header .subline { color: #333333; }
    .answer-table th { background-color: #ffffff; color: #000000; border-top: 2px solid #000000; border-bottom: 2px solid #000000; }
    .answer-row td.q-num { background-color: #ffffff; }
    .pic-num { background-color: #ffffff; color: #000000; border-right: 1px solid #777777; border-bottom: 1px solid #777777; }
"""


def truncate(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def rows_shown(config):
    """Rows every sheet in the pack shows (unused ones are left blank)."""
    return max([MIN_ROWS] + [r.questions for r in config.rounds if r.kind != "picture"])


def row_height(config, total_rows):
    """Answer-row height in px: as tall as fits, up to the layout's cap."""
    layout = config.layout_spec
    width_mm, height_mm = PAPERS[config.paper]
    page_h_mm = width_mm if layout.landscape else height_mm
    cell_h = (page_h_mm - 2 * MARGIN_MM) * MM_TO_PX / layout.rows
    return max(MIN_ROW_PX, min(layout.row_cap, int((cell_h - OVERHEAD_PX) / total_rows)))


def page_plan(config, only_round=None):
    """The pages to print, as (round index, [team index or None per sheet]).

    With teams, page order is either team-packet order (all rounds for one
    group of teams, then the next group) or round order.
    """
    per_page = config.layout_spec.per_page
    if config.teams:
        slots = list(range(config.teams))
        slots += [None] * (-len(slots) % per_page)  # spare, unlabelled sheets
        groups = [slots[i:i + per_page] for i in range(0, len(slots), per_page)]
    else:
        groups = [[None] * per_page]
    rounds = range(len(config.rounds))
    if only_round is not None:
        return [(only_round, groups[0])]
    if config.packet_order == "packets":
        return [(r, g) for g in groups for r in rounds]
    return [(r, g) for r in rounds for g in groups]


def _marks(letters, size):
    style = f'width:{size}px;height:{size}px;line-height:{size - 2}px;'
    return "".join(f'<span class="mark" style="{style}">{letter}</span>' for letter in letters)


def _mc_option_budget(config, rnd):
    """Rough max characters per option, so a Circle One row's real choice text
    always fits on its single-line row — options are truncated to this length
    rather than risking them running off the page."""
    layout = config.layout_spec
    width_mm, height_mm = PAPERS[config.paper]
    page_w_mm = height_mm if layout.landscape else width_mm
    cell_w_px = (page_w_mm - 2 * MARGIN_MM) * MM_TO_PX / layout.cols - SHEET_PADDING_PX
    choices_col_px = cell_w_px * 0.88   # ~100% minus the #-column's 12%
    px_per_char = 4.6                   # rough average glyph width at the options' font size
    per_option_px = choices_col_px / max(1, rnd.choices)
    return max(4, int(per_option_px / px_per_char) - 3)   # -3 reserves room for "X " prefix


def _choice_used_cell(rnd, mark_size, mc_budget):
    """A Circle One row's used-cell for question `i` (1-based): the real
    options when the round has them, truncated to fit one line; bare lettered
    circles otherwise (no options for that question). When the round has real
    options for at least one *other* question, a gap row's circles are left-
    aligned to line up with those option-text rows instead of sitting centered
    on their own — otherwise they stay centered, matching a round with no
    options at all (unchanged from before this feature)."""
    letters = "ABCDEF"[: rnd.choices]
    bare_class = "q-ans q-marks q-left" if any(rnd.mc_options) else "q-ans q-marks"
    bare = f'<td class="{bare_class}">{_marks(letters, mark_size)}</td>'

    def cell(i):
        options = rnd.mc_options[i - 1] if i - 1 < len(rnd.mc_options) else ()
        if not options:
            return bare
        spans = "".join(
            f'<span class="choice"><b>{letters[j]}</b> {escape(truncate(opt, mc_budget))}</span>'
            for j, opt in enumerate(options[: rnd.choices])
        )
        return f'<td class="q-ans q-choices">{spans}</td>'

    return cell


def _table_parts(rnd, mark_size, mc_budget):
    """(head cells, a used-cell-for-question(i) callable, cells of an unused row, column count)."""
    if rnd.kind == "music":
        head = '<th class="num-col">#</th><th class="music-col">Song Name</th><th>Artist</th>'
        blank = '<td class="q-music">&nbsp;</td><td class="q-ans">&nbsp;</td>'
        return head, lambda i: blank, blank, 3
    blank = '<td class="q-ans">&nbsp;</td>'
    if rnd.kind == "truefalse":
        head = '<th class="num-col">#</th><th>True / False</th>'
        used = f'<td class="q-ans q-marks">{_marks("TF", mark_size)}</td>'
        return head, lambda i: used, blank, 2
    if rnd.kind == "choice":
        head = '<th class="num-col">#</th><th>Circle One</th>'
        return head, _choice_used_cell(rnd, mark_size, mc_budget), blank, 2
    head = '<th class="num-col">#</th><th>Your Answer</th>'
    return head, lambda i: blank, blank, 2


def _extra_row(rnd, columns):
    if rnd.extra == "none":
        return ""
    if rnd.extra == "tiebreaker":
        label, hint = "TB", "tiebreaker: closest guess wins"
    else:
        label, hint = "Bonus", 'wager: <span class="wager-box"></span>'
    return (
        f'<tr class="answer-row"><td class="q-num">{label}</td>'
        f'<td class="q-ans q-extra" colspan="{columns - 1}">{hint}</td></tr>'
    )


def _picture_grid(rnd, block_h, per_row):
    per_row = min(per_row, rnd.questions)
    grid_rows = -(-rnd.questions // per_row)
    cell_h = block_h // grid_rows - 4                 # 4px = the table's cell spacing
    frame_h = max(20, cell_h - 18 - 2)                # 18px answer line, 2px frame border
    rows = ""
    for r in range(grid_rows):
        cells = ""
        for c in range(per_row):
            n = r * per_row + c
            if n >= rnd.questions:
                cells += '<td class="pic-cell"></td>'
                continue
            img = f'<img src="{rnd.images[n]}" style="height:{frame_h}px">' if n < len(rnd.images) else f'<div style="height:{frame_h}px"></div>'
            cells += (
                f'<td class="pic-cell"><div class="pic-frame"><div class="pic-num">{n + 1}</div>{img}</div>'
                f'<div class="pic-line"></div></td>'
            )
        rows += f"<tr>{cells}</tr>"
    return f'<table class="pic-grid">{rows}</table>'


def _name_max_px(config):
    """Width left for a team name on the team line, so a long one is clipped
    instead of pushing the score box out of the sheet."""
    layout = config.layout_spec
    width_mm, height_mm = PAPERS[config.paper]
    page_w_mm = height_mm if layout.landscape else width_mm
    cell_w = (page_w_mm - 2 * MARGIN_MM) * MM_TO_PX / layout.cols
    return int(cell_w - SHEET_PADDING_PX - TEAM_LINE_FIXED_PX)


def _team_info(config, rnd, team):
    badge = name = ""
    if team is not None:
        if config.team_mode == "tables":
            badge = f"Table {team + 1}"
        elif config.team_mode == "names":
            name = escape(config.team_names[team])
    badge_cell = f'<div class="team-info-cell badge">{badge}</div>' if badge else ""
    return f"""
            <div class="team-info-box">
                {badge_cell}
                <div class="team-info-cell label">Team:</div>
                <div class="team-info-cell line"><div class="name" style="max-width:{_name_max_px(config)}px">{name}</div></div>
                <div class="team-info-cell score-label">Score:</div>
                <div class="team-info-cell score-box"><span></span></div>
                <div class="team-info-cell score-max">/ {rnd.max_points}</div>
            </div>"""


def _sheet_html(config, rnd, team, shown):
    extra_rows = 1 if rnd.extra != "none" else 0
    height = row_height(config, shown + extra_rows)
    mark_size = min(16, height - 8)
    mc_budget = _mc_option_budget(config, rnd) if rnd.kind == "choice" else 0
    head, used, unused, columns = _table_parts(rnd, mark_size, mc_budget)

    if rnd.kind == "picture":
        per_row = 5 if config.layout == "4up" else 4
        body = _picture_grid(rnd, shown * height + THEAD_PX, per_row)  # the block replaces the column heads too
        if extra_rows:
            body += f'<table class="answer-table"><colgroup><col style="width:12%"><col></colgroup><tbody>{_extra_row(rnd, 2)}</tbody></table>'
    else:
        rows = ""
        for i in range(1, shown + 1):
            if i <= rnd.questions:
                rows += f'<tr class="answer-row"><td class="q-num">{i}</td>{used(i)}</tr>'
            else:
                rows += f'<tr class="answer-row"><td class="q-num">&nbsp;</td>{unused}</tr>'
        rows += _extra_row(rnd, columns)
        body = f'<table class="answer-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'

    subline = " · ".join(p for p in (f"{rnd.points} pts each" if rnd.points != 1 else "", truncate(config.event_line, SUBLINE_MAX)) if p)
    subline_html = f'<div class="subline">{escape(subline)}</div>' if subline else ""
    logo_html = f'<img class="logo" src="{config.logo}">' if config.logo else ""
    header_class = "header has-logo" if config.logo else "header"

    return f"""
        <div class="sheet-wrapper rh-{height}">
            <div class="{header_class}">{logo_html}<h1>{escape(rnd.name)}</h1>{subline_html}</div>
            {_team_info(config, rnd, team)}
            {body}
        </div>
        """


def _css(config, heights):
    layout = config.layout_spec
    paper = config.paper.lower()
    css = (
        BASE_CSS.replace("@@PAGE_SIZE@@", f"{paper} {'landscape' if layout.landscape else 'portrait'}")
        .replace("@@MARGIN@@", str(MARGIN_MM))
        .replace("@@CELL_W@@", f"{100 / layout.cols:g}")
        .replace("@@CELL_H@@", f"{100 / layout.rows:g}")
    )
    for h in sorted(heights):
        css += f"    .rh-{h} .answer-row td {{ height: {h}px; }}\n"
    if config.ink_saver:
        css += INK_SAVER_CSS
    return css


def generate_trivia_html(config, only_round=None):
    """Return a full HTML document for the pack: one page per entry in
    `page_plan(config)`, each a grid of sheets. With `only_round`, just the
    first page of that round (used for the live preview)."""
    layout = config.layout_spec
    shown = rows_shown(config)
    body_content = ""
    heights = set()
    for round_index, teams in page_plan(config, only_round):
        rnd = config.rounds[round_index]
        heights.add(row_height(config, shown + (1 if rnd.extra != "none" else 0)))
        sheets = [f'<td class="grid-cell">{_sheet_html(config, rnd, t, shown)}</td>' for t in teams]
        grid_rows = "".join(
            f"<tr>{''.join(sheets[r * layout.cols:(r + 1) * layout.cols])}</tr>" for r in range(layout.rows)
        )
        body_content += f'\n        <table class="master-grid">{grid_rows}</table>\n        '
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{_css(config, heights)}</style>
</head>
<body>
{body_content}</body></html>"""
