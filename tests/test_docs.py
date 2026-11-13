"""The documents are part of the product: a reference that rots fails the suite.

Checks for specs/library: relative links and anchors resolve; every `file::test` reference names a real test; every edge case of the
register appears in a test; every edge case or requirement cited elsewhere is defined; every Mermaid diagram carries the pastel theme.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = sorted((ROOT / "specs" / "library").glob("*.md"))
TESTS = sorted((ROOT / "tests").glob("test_*.py"))
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"```.*?```", re.S)


def slug(heading: str) -> str:
    text = heading.strip().lower().replace("`", "")
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path: pathlib.Path) -> set[str]:
    text = FENCE.sub("", path.read_text())
    return {slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.*)$", text, re.M)}


def prose(path: pathlib.Path) -> str:
    return FENCE.sub("", path.read_text())


def test_there_are_fourteen_documents_and_a_readme():
    assert [d.name for d in DOCS][0] == "00-five-whys-and-first-principles.md" and len(DOCS) == 15
    assert "README.md" in [d.name for d in DOCS]


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_every_relative_link_and_anchor_resolves(doc):
    broken = []
    for target in LINK.findall(prose(doc)):
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
    defined = {path.name: set(re.findall(r"^def (test_\w+)", path.read_text(), re.M)) for path in TESTS}
    cited = []
    for doc in DOCS:
        cited += [(doc.name, m.group(1), m.group(2)) for m in re.finditer(r"(test_\w+\.py)::(test_\w+)", doc.read_text())]
    assert len(cited) > 60
    missing = [c for c in cited if c[1] not in defined or c[2] not in defined[c[1]]]
    assert missing == []


def register_ids() -> list[str]:
    text = (ROOT / "specs" / "library" / "10-edge-cases-and-state-charts.md").read_text()
    section = text.split("## Register")[1].split("## Request lifecycle")[0]
    return re.findall(r"^\| (EC-L-\d\d) \|", section, re.M)


def test_the_register_has_thirty_three_distinct_edge_cases():
    ids = register_ids()
    assert len(ids) == len(set(ids)) == 33 and sorted(ids) == [f"EC-L-{i:02d}" for i in range(1, 34)]


def test_every_registered_edge_case_appears_in_a_test():
    body = "\n".join(path.read_text() for path in TESTS)
    assert [i for i in register_ids() if i not in body] == []


def test_every_cited_edge_case_and_requirement_is_defined():
    defined_ec = set(register_ids())
    requirements = (ROOT / "specs" / "library" / "02-requirements-and-traceability.md").read_text()
    defined_req = set(re.findall(r"^\| (REQ-L-\d\d) \|", requirements, re.M))
    cited_ec, cited_req = set(), set()
    for doc in DOCS:
        text = doc.read_text()
        cited_ec |= set(re.findall(r"EC-L-\d\d", text))
        cited_req |= set(re.findall(r"REQ-L-\d\d", text))
    assert cited_ec - defined_ec == set() and cited_req - defined_req == set()
    assert len(defined_req) == 14


def test_every_requirement_names_at_least_one_test():
    text = (ROOT / "specs" / "library" / "02-requirements-and-traceability.md").read_text()
    rows = re.findall(r"^\| (REQ-L-\d\d) \|.*$", text, re.M)
    assert rows
    for row in re.finditer(r"^\| (REQ-L-\d\d) \|(.*)$", text, re.M):
        assert "test_" in row.group(2), f"{row.group(1)} cites no test"


def test_every_mermaid_diagram_uses_the_pastel_theme():
    count = 0
    for doc in DOCS:
        for block in re.findall(r"```mermaid\n(.*?)```", doc.read_text(), re.S):
            count += 1
            assert block.startswith("%%{init:") and "'theme':'base'" in block, f"{doc.name}: a diagram without the pastel init"
            assert re.search(r"#(DCEBFA|DDF2E3|FDE7D5|E8E0F7|FADCE6|FFF6D6|D9F2EC|B8D4F0|F5C9A8)", block), f"{doc.name}: no pastel colour"
    assert count >= 18


def test_ascii_wireframes_exist_for_the_screens():
    text = (ROOT / "specs" / "library" / "07-cli-and-ux.md").read_text()
    assert text.count("┌") >= 6 and "edgekpi --+-- validate MODEL" in text
