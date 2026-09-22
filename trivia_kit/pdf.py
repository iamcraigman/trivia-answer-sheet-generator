"""PDF rendering, with two backends available on Windows.

- "library": `import weasyprint` directly. This needs WeasyPrint's native
  libraries (Pango, cairo, ...) to be reachable, e.g. via an MSYS2 install
  (see the README) — `configure_weasyprint_dlls()` below points at that
  install before the import happens.
- "standalone": shells out to WeasyPrint's self-contained release executable
  (https://github.com/Kozea/WeasyPrint/releases), which bundles those
  libraries, so no MSYS2 install is needed at all. Used only when the
  library import fails *and* WEASYPRINT_STANDALONE_EXE points at that
  executable, so an existing MSYS2 install is unaffected either way.
"""
import os
import subprocess

STANDALONE_EXE_ENV_VAR = "WEASYPRINT_STANDALONE_EXE"

# MSYS2 ships several independent environments (UCRT64, MINGW64, ...). Its
# installer creates a `bin` folder for all of them regardless of what's
# actually installed, so an empty UCRT64 folder can't be told apart from a
# real install by its existence alone — this checks for one of pango's DLLs,
# the package both this project's README and WeasyPrint's own docs have you
# install, instead. WeasyPrint's docs now recommend UCRT64; MINGW64 is kept
# as a fallback for installs set up before that switch (this project
# originally shipped pointing only at MINGW64).
DEFAULT_MSYS2_BIN_DIRS = (r"C:\msys64\ucrt64\bin", r"C:\msys64\mingw64\bin")
MSYS2_MARKER_DLL = "libpango-1.0-0.dll"


def configure_weasyprint_dlls():
    """Point WeasyPrint at its native libraries on Windows.

    A WEASYPRINT_DLL_DIRECTORIES value already in the environment wins, so a
    non-default install can be used without editing code. Must run before
    `weasyprint` is imported.
    """
    if os.name != "nt" or os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        return
    for path in DEFAULT_MSYS2_BIN_DIRS:
        if os.path.isfile(os.path.join(path, MSYS2_MARKER_DLL)):
            os.environ["WEASYPRINT_DLL_DIRECTORIES"] = path
            return


configure_weasyprint_dlls()

_standalone_exe = os.environ.get(STANDALONE_EXE_ENV_VAR, "").strip()

try:
    from weasyprint import HTML as _HTML  # noqa: E402  (must follow the DLL setup above)
    _backend = "library"
except (ImportError, OSError) as exc:
    # Only take the standalone path if it's explicitly configured and real, so an
    # environment with neither backend available still fails immediately and
    # clearly here, exactly as before, instead of on the first render attempt.
    if not _standalone_exe:
        raise
    if not os.path.isfile(_standalone_exe):
        raise ImportError(
            f"{STANDALONE_EXE_ENV_VAR} is set to '{_standalone_exe}', but that file doesn't exist."
        ) from exc
    _HTML = None
    _backend = "standalone"


def backend():
    """Which backend is rendering PDFs: "library" or "standalone"."""
    return _backend


def render_document(html):
    """Render `html` and return a WeasyPrint Document (page objects, etc).
    Only the library backend can produce this."""
    if _backend != "library":
        raise RuntimeError("render_document() needs the WeasyPrint library backend, not the standalone executable.")
    return _HTML(string=html).render()


def _run_standalone_exe(exe_path, html):
    """Run the standalone WeasyPrint executable on `html` (via stdin/stdout,
    so nothing touches disk) and return its PDF bytes."""
    result = subprocess.run(
        [exe_path, "-e", "utf-8", "-", "-"],
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not result.stdout.startswith(b"%PDF"):
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError(f"The standalone WeasyPrint executable failed: {detail[-1] if detail else 'no output'}")
    return result.stdout


def _count_pdf_pages(pdf_bytes):
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf_bytes)
    try:
        return len(document)
    finally:
        document.close()


def build_pdf(html):
    """Return (PDF bytes, page count)."""
    if _backend == "library":
        document = render_document(html)
        return document.write_pdf(), len(document.pages)
    pdf = _run_standalone_exe(_standalone_exe, html)
    return pdf, _count_pdf_pages(pdf)


def html_to_pdf(html):
    return build_pdf(html)[0]


def pdf_to_pngs(pdf_bytes, max_pages=None, scale=1.4):
    """Rasterize a PDF's pages (the first `max_pages`) to PNG bytes."""
    import io

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        pngs = []
        for i in range(len(pdf) if max_pages is None else min(max_pages, len(pdf))):
            out = io.BytesIO()
            pdf[i].render(scale=scale).to_pil().save(out, format="PNG")
            pngs.append(out.getvalue())
        return pngs
    finally:
        pdf.close()
