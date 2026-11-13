"""Build why-a-sql-query-is-not-a-kpi.pdf from its HTML source and set the document metadata.

Chrome prints the pages; it does not copy the HTML author into the PDF, so the metadata is written here.
Run from anywhere:
    uv run --with pypdf python specs/kpi/briefing/build_pdf.py
"""
import pathlib
import subprocess
import tempfile

from pypdf import PdfReader, PdfWriter

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "why-a-sql-query-is-not-a-kpi.html"
TARGET = HERE / "why-a-sql-query-is-not-a-kpi.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
METADATA = {
    "/Title": "A SQL query is not a KPI",
    "/Author": "Raphael MANSUY",
    "/Subject": "Why a parameterised SQL query is not the right place to define a KPI, and what to use instead",
}

with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    printed = pathlib.Path(tmp) / "printed.pdf"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
         f"--print-to-pdf={printed}", SOURCE.as_uri()],
        check=True, capture_output=True,
    )
    writer = PdfWriter(clone_from=PdfReader(printed))
    writer.add_metadata(METADATA)
    with TARGET.open("wb") as out:
        writer.write(out)

info = PdfReader(TARGET)
print(f"{TARGET.name}: {len(info.pages)} pages, author {info.metadata.author!r}, title {info.metadata.title!r}")
