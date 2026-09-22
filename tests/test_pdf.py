import io

import pytest
from PIL import Image

from trivia_kit.sheets import generate_trivia_html, page_plan
from trivia_kit.images import to_data_uri
from trivia_kit.models import FORMATS, LAYOUTS, PAPERS, EventConfig, Round

try:
    from trivia_kit.pdf import build_pdf, html_to_pdf, pdf_to_pngs, render_document
except (ImportError, OSError) as exc:  # WeasyPrint or its system libraries are missing
    pytest.skip(f"WeasyPrint unavailable: {exc}", allow_module_level=True)


def test_one_landscape_page_per_round():
    rounds = tuple(Round(f"Round {i}", "music" if i % 2 == 0 else "single") for i in range(1, 6))
    pages = render_document(generate_trivia_html(EventConfig(rounds=rounds))).pages
    assert len(pages) == 5
    assert all(p.width > p.height for p in pages)


def test_single_round_has_no_trailing_blank_page():
    assert len(render_document(generate_trivia_html(EventConfig(rounds=(Round("Solo"),)))).pages) == 1


def test_markup_in_round_name_does_not_break_render():
    pdf = html_to_pdf(generate_trivia_html(EventConfig(rounds=(Round("<b>Bold</b> & <script>x</script>", questions=3),))))
    assert pdf.startswith(b"%PDF")


def _tile():
    out = io.BytesIO()
    Image.new("RGB", (60, 40), (200, 30, 30)).save(out, format="PNG")
    return to_data_uri(out.getvalue(), 300)


@pytest.mark.parametrize("layout", list(LAYOUTS))
@pytest.mark.parametrize("paper", list(PAPERS))
@pytest.mark.parametrize("team_mode", ["names", "tables"])
def test_worst_case_content_never_spills_onto_extra_pages(layout, paper, team_mode):
    """Every format with the longest names, a logo, a tiebreaker or wager on each round,
    the most rows the layout allows, and an uneven number of teams."""
    tile = _tile()
    most = LAYOUTS[layout].max_questions
    rounds = tuple(
        Round("W" * 40, kind, most, 99, "tiebreaker" if i % 2 else "wager", 6, (tile,) * 20 if kind == "picture" else ())
        for i, kind in enumerate(FORMATS)
    )
    config = EventConfig(
        rounds=rounds, title="W" * 40, date="W" * 40, venue="W" * 40, logo=tile, paper=paper, layout=layout,
        team_mode=team_mode, num_teams=5, team_names=("W" * 40,) * 5,
    )
    _, pages = build_pdf(generate_trivia_html(config))
    assert pages == len(page_plan(config)) > len(rounds)


def test_ink_saver_and_a4_render():
    config = EventConfig(rounds=(Round("A"),), paper="A4", ink_saver=True, layout="2up")
    assert build_pdf(generate_trivia_html(config))[1] == 1


def test_pdf_to_pngs_rasterizes_the_requested_pages():
    pytest.importorskip("pypdfium2")
    pdf, pages = build_pdf(generate_trivia_html(EventConfig(rounds=tuple(Round(f"R{i}") for i in range(3)))))
    assert pages == 3
    pngs = pdf_to_pngs(pdf, max_pages=2)
    assert len(pngs) == 2 and all(p.startswith(b"\x89PNG") for p in pngs)
