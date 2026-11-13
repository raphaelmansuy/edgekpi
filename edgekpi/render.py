"""Text rendering of a grid as a pivot table: the reader-facing view of the long result (docs: 09-cli-and-ux)."""
from __future__ import annotations

from .grid import Grid
from .request import Report


def _member(value) -> str:
    return "(none)" if value is None else str(value)


def _sort_key(key: tuple, depth: int) -> tuple:
    # children first, then their subtotal, the grand total last: pad shorter keys with a high sentinel
    padded = [(1, _member(m)) if m is not None else (0, "") for m in key] + [(2, "")] * (depth - len(key))
    return tuple(padded)


def _label(key: tuple, depth: int, total_word: str) -> str:
    if not key:
        return total_word
    text = " / ".join(_member(m) for m in key)
    return text if len(key) == depth else f"{text} / total"


def format_value(value, fmt: str) -> str:
    if value is None:
        return "-"
    if fmt == "percent":
        return f"{value * 100:.1f}%"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.2f}"


def pivot_text(report: Report, grid: Grid, name: str) -> str:
    """One table for one KPI or measure: row dimensions down, column dimensions across, every requested total."""
    model = report.model
    kpi = model.kpi(name)
    fmt = kpi.format if kpi else "number"
    title = (kpi.label if kpi and kpi.label else name)
    rows, cols = report.request.rows, report.request.cols
    cells: dict[tuple, str] = {}
    row_keys, col_keys = set(), set()
    for node, values in grid.cells.items():
        split = dict(node.key)
        row_key = tuple(split[d] for d in rows if d in split)
        col_key = tuple(split[d] for d in cols if d in split)
        cells[(row_key, col_key)] = format_value(values[name], fmt)
        row_keys.add(row_key)
        col_keys.add(col_key)
    row_order = sorted(row_keys, key=lambda k: _sort_key(k, len(rows)))
    col_order = sorted(col_keys, key=lambda k: _sort_key(k, len(cols)))
    header = [" / ".join(rows) or title] + [_label(c, len(cols), "All" if cols else title) for c in col_order]
    body = [[_label(r, len(rows), "Total")] + [cells.get((r, c), "") for c in col_order] for r in row_order]
    widths = [max(len(line[i]) for line in [header, *body]) for i in range(len(header))]

    def line(items):
        return "| " + " | ".join(item.ljust(widths[0]) if i == 0 else item.rjust(widths[i]) for i, item in enumerate(items)) + " |"

    rule = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    return "\n".join([title, rule, line(header), rule, *[line(b) for b in body], rule])
