import io
import os

import pytest
from PIL import Image

from trivia_kit.sheets import generate_trivia_html, page_plan
from trivia_kit.images import to_data_uri
from trivia_kit.models import FORMATS, LAYOUTS, PAPERS, EventConfig, Round

try:
    from trivia_kit import pdf as pdf_module
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


def test_backend_is_whichever_this_environment_actually_uses():
    # This project's dev/CI environment has a working WeasyPrint install, so the
    # library backend is the one exercised by every other test in this file.
    assert pdf_module.backend() == "library"


class TestConfigureWeasyprintDlls:
    """`configure_weasyprint_dlls()` runs once at import time in the real app; these
    call it directly under simulated conditions, matching v70's documented Windows
    install (https://doc.courtbouillon.org/weasyprint/stable/first_steps.html),
    which points at the UCRT64 MSYS2 environment rather than the older MINGW64 one."""

    def _fake_isfile(self, populated_dirs):
        marker = pdf_module.MSYS2_MARKER_DLL
        populated = {os.path.join(d, marker) for d in populated_dirs}
        return lambda p: p in populated

    def test_prefers_ucrt64_over_mingw64(self, monkeypatch):
        monkeypatch.setattr(pdf_module.os, "name", "nt")
        monkeypatch.delenv("WEASYPRINT_DLL_DIRECTORIES", raising=False)
        monkeypatch.setattr(pdf_module.os.path, "isfile", self._fake_isfile(pdf_module.DEFAULT_MSYS2_BIN_DIRS))
        pdf_module.configure_weasyprint_dlls()
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"] == r"C:\msys64\ucrt64\bin"

    def test_falls_back_to_mingw64_when_ucrt64_is_absent(self, monkeypatch):
        monkeypatch.setattr(pdf_module.os, "name", "nt")
        monkeypatch.delenv("WEASYPRINT_DLL_DIRECTORIES", raising=False)
        monkeypatch.setattr(pdf_module.os.path, "isfile", self._fake_isfile([r"C:\msys64\mingw64\bin"]))
        pdf_module.configure_weasyprint_dlls()
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"] == r"C:\msys64\mingw64\bin"

    def test_an_empty_ucrt64_folder_is_not_mistaken_for_an_install(self, monkeypatch):
        """Regression test: MSYS2's installer creates a `ucrt64\\bin` folder for every
        environment whether or not anything was installed into it, so a bare
        `isdir()` check picks that empty folder over a real MINGW64 install and
        breaks WeasyPrint. Caught by testing this against a real MSYS2 install that
        only had MINGW64 set up, where `ucrt64\\bin` existed but was empty."""
        monkeypatch.setattr(pdf_module.os, "name", "nt")
        monkeypatch.delenv("WEASYPRINT_DLL_DIRECTORIES", raising=False)
        monkeypatch.setattr(pdf_module.os.path, "isdir", lambda p: True)  # both folders exist ...
        monkeypatch.setattr(pdf_module.os.path, "isfile", self._fake_isfile([r"C:\msys64\mingw64\bin"]))  # ... only one is populated
        pdf_module.configure_weasyprint_dlls()
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"] == r"C:\msys64\mingw64\bin"

    def test_leaves_nothing_set_when_neither_is_populated(self, monkeypatch):
        monkeypatch.setattr(pdf_module.os, "name", "nt")
        monkeypatch.delenv("WEASYPRINT_DLL_DIRECTORIES", raising=False)
        monkeypatch.setattr(pdf_module.os.path, "isdir", lambda p: True)
        monkeypatch.setattr(pdf_module.os.path, "isfile", lambda p: False)
        pdf_module.configure_weasyprint_dlls()
        assert "WEASYPRINT_DLL_DIRECTORIES" not in os.environ

    def test_an_existing_value_is_never_overwritten(self, monkeypatch):
        monkeypatch.setattr(pdf_module.os, "name", "nt")
        monkeypatch.setenv("WEASYPRINT_DLL_DIRECTORIES", r"C:\custom\install")
        monkeypatch.setattr(pdf_module.os.path, "isfile", lambda p: True)
        pdf_module.configure_weasyprint_dlls()
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"] == r"C:\custom\install"

    def test_does_nothing_off_windows(self, monkeypatch):
        monkeypatch.setattr(pdf_module.os, "name", "posix")
        monkeypatch.delenv("WEASYPRINT_DLL_DIRECTORIES", raising=False)
        monkeypatch.setattr(pdf_module.os.path, "isfile", lambda p: True)
        pdf_module.configure_weasyprint_dlls()
        assert "WEASYPRINT_DLL_DIRECTORIES" not in os.environ


class TestRunStandaloneExe:
    """Unit tests for the standalone-executable backend's subprocess plumbing,
    against a faked `subprocess.run` rather than a real binary (31MB, and only
    runs on Windows, so it isn't a fit for the test suite). Verified for real,
    outside this suite: downloading v70.0's official release exe from
    https://github.com/Kozea/WeasyPrint/releases and comparing its PDF output
    (page count and a visual check) against this project's library backend for
    the same generated pack, including a picture round and non-ASCII team names."""

    class FakeCompletedProcess:
        def __init__(self, returncode, stdout=b"", stderr=b""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def test_returns_pdf_bytes_on_success(self, monkeypatch):
        monkeypatch.setattr(
            pdf_module.subprocess, "run", lambda *a, **k: self.FakeCompletedProcess(0, stdout=b"%PDF-1.7 fake")
        )
        assert pdf_module._run_standalone_exe("fake.exe", "<html></html>") == b"%PDF-1.7 fake"

    def test_sends_html_via_stdin_utf8_and_requests_stdin_stdout(self, monkeypatch):
        captured = {}

        def fake_run(cmd, input, stdout, stderr):
            captured["cmd"], captured["input"] = cmd, input
            return self.FakeCompletedProcess(0, stdout=b"%PDF-1.7")

        monkeypatch.setattr(pdf_module.subprocess, "run", fake_run)
        pdf_module._run_standalone_exe(r"C:\tools\weasyprint.exe", "<html>café</html>")
        assert captured["cmd"][0] == r"C:\tools\weasyprint.exe"
        assert captured["cmd"][-2:] == ["-", "-"]          # positional stdin/stdout markers
        assert captured["input"] == "<html>café</html>".encode("utf-8")

    def test_raises_with_the_executables_stderr_on_a_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(
            pdf_module.subprocess, "run",
            lambda *a, **k: self.FakeCompletedProcess(1, stderr=b"Traceback...\nFileNotFoundError: input.html"),
        )
        with pytest.raises(RuntimeError, match="FileNotFoundError"):
            pdf_module._run_standalone_exe("fake.exe", "<html></html>")

    def test_raises_when_exit_is_zero_but_output_is_not_a_pdf(self, monkeypatch):
        monkeypatch.setattr(pdf_module.subprocess, "run", lambda *a, **k: self.FakeCompletedProcess(0, stdout=b""))
        with pytest.raises(RuntimeError):
            pdf_module._run_standalone_exe("fake.exe", "<html></html>")
