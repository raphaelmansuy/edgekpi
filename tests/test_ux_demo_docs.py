"""The documents of specs/ux-demo are part of the product: a reference that rots fails the suite.

Checks: links, anchors and images resolve; every cited test and screenshot exists; the register of edge cases is complete and each
case appears in a test; requirements name tests; every Mermaid diagram carries the pastel theme; the wireframes are present.
"""
import pathlib
import re

import pytest
from test_docs import FENCE, LINK, anchors, prose

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOLDER = ROOT / "specs" / "ux-demo"
DOCS = sorted(FOLDER.glob("*.md"))
SHOTS = FOLDER / "e2e" / "screenshots"
WEB = ROOT / "demo" / "web"
TS_TESTS = sorted((WEB / "e2e" / "tests").glob("*.spec.ts")) + sorted((WEB / "src").rglob("*.test.ts"))
PY_TESTS = sorted((ROOT / "tests").glob("test_*.py"))
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")


def read(path: pathlib.Path) -> str:
    return path.read_text()


def test_there_are_eleven_numbered_documents_and_a_readme():
    names = [d.name for d in DOCS]
    assert names[0] == "00-five-whys-and-first-principles.md" and "README.md" in names and len(names) == 12


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_relative_link_anchor_and_image_resolves(doc):
    broken = []
    for target in LINK.findall(prose(doc)) + IMAGE.findall(prose(doc)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        resolved = (doc.parent / path).resolve() if path else doc
        if not resolved.exists():
            broken.append(target)
        elif anchor and resolved.suffix == ".md" and anchor not in anchors(resolved):
            broken.append(target)
    assert broken == [], f"{doc.name}: {broken}"


def test_every_cited_test_exists():
    ts_text = {p.name: read(p) for p in TS_TESTS}
    py_defs = {p.name: set(re.findall(r"^def (test_\w+)", read(p), re.M)) for p in PY_TESTS}
    cited_ts, cited_py = [], []
    for doc in DOCS:
        text = read(doc)
        cited_ts += [(doc.name, m.group(1), m.group(2).strip()) for m in re.finditer(r"`(\w+\.(?:spec|test)\.ts)::([^`]+)`", text)]
        cited_py += [(doc.name, m.group(1), m.group(2)) for m in re.finditer(r"(test_\w+\.py)::(test_\w+)", text)]
    assert len(cited_ts) > 40 and len(cited_py) > 8
    assert [c for c in cited_ts if c[1] not in ts_text or c[2] not in ts_text[c[1]]] == []
    assert [c for c in cited_py if c[1] not in py_defs or c[2] not in py_defs[c[1]]] == []


def register_ids() -> list[str]:
    text = read(FOLDER / "06-edge-cases-and-state-charts.md")
    section = text.split("## Register")[1].split("## A call from the screen")[0]
    return re.findall(r"^\| (EC-D-\d\d) \|", section, re.M)


def test_the_register_has_thirty_distinct_edge_cases():
    ids = register_ids()
    assert len(ids) == len(set(ids)) == 30 and sorted(ids) == [f"EC-D-{i:02d}" for i in range(1, 31)]


def test_every_registered_edge_case_appears_in_a_test():
    body = "\n".join(read(p) for p in TS_TESTS + PY_TESTS)
    assert [i for i in register_ids() if i not in body] == []


def test_every_register_row_names_a_proof():
    text = read(FOLDER / "06-edge-cases-and-state-charts.md")
    section = text.split("## Register")[1].split("## A call from the screen")[0]
    for row in re.finditer(r"^\| (EC-D-\d\d) \|(.*)$", section, re.M):
        assert "::" in row.group(2), f"{row.group(1)} cites no test"


def test_every_cited_edge_case_and_requirement_is_defined():
    defined_req = set(re.findall(r"^\| (REQ-D-\d\d) \|", read(FOLDER / "02-requirements-and-traceability.md"), re.M))
    cited_ec, cited_req = set(), set()
    for doc in DOCS:
        text = read(doc)
        cited_ec |= set(re.findall(r"EC-D-\d\d", text))
        cited_req |= set(re.findall(r"REQ-D-\d\d", text))
    assert cited_ec - set(register_ids()) == set() and cited_req - defined_req == set() and len(defined_req) == 15


def test_every_requirement_names_a_test():
    for row in re.finditer(r"^\| (REQ-D-\d\d) \|(.*)$", read(FOLDER / "02-requirements-and-traceability.md"), re.M):
        cells = row.group(2)
        assert "::" in cells or "test_" in cells, f"{row.group(1)} cites no test"


def test_every_cited_screenshot_exists_and_none_is_orphaned():
    shots = {p.name for p in SHOTS.glob("*.png")}
    cited = set()
    for doc in DOCS:
        cited |= {pathlib.Path(t).name for t in IMAGE.findall(prose(doc)) + LINK.findall(prose(doc)) if t.endswith(".png")}
    assert cited - shots == set(), "a cited screenshot is missing"
    log = read(FOLDER / "09-visual-inspection-log.md")
    assert [s for s in sorted(shots) if s.removesuffix(".png") not in log] == [], "a screenshot is not in the log"
    assert len(shots) >= 45


def test_every_mermaid_diagram_uses_the_pastel_theme():
    count = 0
    for doc in DOCS:
        for block in re.findall(r"```mermaid\n(.*?)```", read(doc), re.S):
            count += 1
            assert block.startswith("%%{init:") and "'theme':'base'" in block, f"{doc.name}: a diagram without the pastel init"
            assert re.search(r"#(DCEBFA|DDF2E3|FDE7D5|E8E0F7|FADCE6|FFF6D6|D9F2EC)", block), f"{doc.name}: no pastel colour"
    assert count >= 18


def test_ascii_wireframes_and_the_navigation_map_are_present():
    text = read(FOLDER / "05-screens-and-navigation.md")
    assert len(FENCE.findall(text)) >= 8 and text.count("┌") >= 12
    for screen in ("## 1. Report", "## 2. Catalogue", "## 3. Backends", "## 4. Migration", "## 5. Assistant", "## 6. Edge-case lab", "## 7. Tutorial"):
        assert screen in text
