"""PDF rendering via WeasyPrint, including its Windows DLL lookup."""
import os

# Default location of the MSYS2 (mingw64) libraries WeasyPrint needs on Windows.
DEFAULT_MSYS2_BIN = r"C:\msys64\mingw64\bin"


def configure_weasyprint_dlls():
    """Point WeasyPrint at the MSYS2 libraries on Windows.

    A WEASYPRINT_DLL_DIRECTORIES value already in the environment wins, so a
    non-default install can be used without editing code. Must run before
    `weasyprint` is imported.
    """
    if os.name != "nt" or os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        return
    if os.path.isdir(DEFAULT_MSYS2_BIN):
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = DEFAULT_MSYS2_BIN


configure_weasyprint_dlls()

from weasyprint import HTML  # noqa: E402  (must follow the DLL setup above)


def render_document(html):
    return HTML(string=html).render()


def build_pdf(html):
    """Return (PDF bytes, page count)."""
    document = render_document(html)
    return document.write_pdf(), len(document.pages)


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
