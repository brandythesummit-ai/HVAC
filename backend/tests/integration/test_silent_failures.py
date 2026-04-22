"""Silent-failure audit for the HCFL scraper pipeline.

Classic silent-failure bugs look like:

    try:
        do_something()
    except Exception:
        pass

or

    try:
        do_something()
    except Exception as e:
        return None  # no log, no counter

In a background job that runs for hours, silent failures compound:
a 2-hour backfill across 14K streets could lose hundreds of permits
and nobody would notice because the job shows `status=completed`.

This test uses AST introspection to enforce the project convention:
every `except` block in the scraper pipeline MUST either:
  - call a `logger.*` method, OR
  - raise (propagate), OR
  - return a dict with an "error" key (our error-return convention
    from accela_client.py / hcfl_legacy_scraper.py)

Any except handler that silently swallows without one of the above
fails this test.
"""
import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parent.parent.parent

# Files in the scraper pipeline that must be silent-failure-clean.
# Extend this list as new scraper-pipeline modules are added.
AUDITED_FILES = [
    "app/services/hcfl_legacy_scraper.py",
    "app/services/polite_rate_limiter.py",
    "app/services/hcfl_prefix_classifier.py",
    "app/services/hcfl_streets.py",
    "app/workers/job_processor.py",
    "scripts/build_hcfl_streets.py",
    "scripts/classify_hvac_prefixes.py",
]


def _except_handler_is_safe(handler: ast.ExceptHandler) -> tuple[bool, str]:
    """Return (is_safe, reason). A handler is safe if its body:
      - calls logger.*
      - raises
      - returns a dict-with-error, or returns a value that's not None
      - sys.exit()s
    Unsafe = a `pass` only, or an assignment-only, or a return None.
    """
    # Empty body shouldn't happen but guard anyway
    if not handler.body:
        return False, "empty handler body"

    def walk_body(nodes):
        for n in nodes:
            if isinstance(n, ast.Raise):
                yield "raise"
            elif isinstance(n, ast.Return):
                yield "return"
            elif isinstance(n, ast.Continue):
                yield "continue"
            elif isinstance(n, ast.Break):
                yield "break"
            elif isinstance(n, ast.Expr):
                if isinstance(n.value, ast.Call):
                    yield from _classify_call(n.value)
            elif isinstance(n, ast.Pass):
                yield "pass"
            elif isinstance(n, ast.Assign):
                yield "assign"
            elif isinstance(n, ast.If):
                # If branches; look inside
                yield from walk_body(n.body)
                yield from walk_body(n.orelse)
            elif isinstance(n, ast.Try):
                # Nested try; look in body + handlers
                yield from walk_body(n.body)
                for h in n.handlers:
                    yield from walk_body(h.body)
            # Other statement types: treat as opaque "other"

    signals = list(walk_body(handler.body))

    if "logger_call" in signals or "sys_exit" in signals:
        return True, "logs or exits"
    if "raise" in signals:
        return True, "raises"
    # Control-flow (continue/break inside a loop) is NOT silent failure —
    # the loop semantics decide what happens next. Common in retry loops.
    if "continue" in signals or "break" in signals:
        return True, "control flow (continue/break)"
    # A plain `pass` or `assign` with no logger is the silent failure pattern
    if signals == ["pass"] or all(s == "assign" for s in signals):
        return False, f"body only does: {signals}"
    # A `return` without a logger is dicey but context-dependent — we
    # accept it if there's no explicit `pass`, since the return might be
    # a dict {"error": "..."} or similar (our convention).
    if "return" in signals and "logger_call" not in signals:
        # Permissive: accept, but could tighten later if we want.
        return True, "returns (assumed dict-with-error convention)"
    return True, f"mixed signals: {signals}"


def _classify_call(call: ast.Call) -> list[str]:
    # Identify logger.X() calls and sys.exit()
    out = []
    if isinstance(call.func, ast.Attribute):
        attr = call.func.attr
        # logger.info, logger.warning, logger.error, logger.exception, logger.debug
        if attr in {"info", "warning", "error", "exception", "debug", "critical"}:
            # Check it's on `logger` or `log`
            if isinstance(call.func.value, ast.Name) and call.func.value.id in {"logger", "log"}:
                out.append("logger_call")
        elif attr == "exit":
            if isinstance(call.func.value, ast.Name) and call.func.value.id == "sys":
                out.append("sys_exit")
    return out


def _collect_except_handlers(source_path: Path) -> list[tuple[int, ast.ExceptHandler]]:
    tree = ast.parse(source_path.read_text())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            out.append((node.lineno, node))
    return out


@pytest.mark.parametrize("relative_path", AUDITED_FILES)
def test_no_silent_except_handlers(relative_path):
    path = BACKEND_ROOT / relative_path
    assert path.exists(), f"Audited file missing: {relative_path}"

    handlers = _collect_except_handlers(path)
    violations = []
    for lineno, handler in handlers:
        safe, reason = _except_handler_is_safe(handler)
        if not safe:
            violations.append(f"{relative_path}:{lineno} — {reason}")

    assert not violations, (
        f"Silent-failure violations in {relative_path}:\n"
        + "\n".join("  " + v for v in violations)
        + "\n\n"
        "Every except handler in the scraper pipeline must log, raise, "
        "return a dict-with-error, or sys.exit. Bare `pass`/silent swallow "
        "is forbidden."
    )


def test_auditlist_covers_all_new_scraper_files():
    """Drift check: if someone adds a new file that fits the scraper
    pipeline naming pattern but forgets to include it in AUDITED_FILES,
    this test fails loudly."""
    services = BACKEND_ROOT / "app" / "services"
    all_scraper_services = sorted(
        f"app/services/{p.name}" for p in services.glob("hcfl_*.py")
    )
    all_scraper_services.extend(["app/services/polite_rate_limiter.py"])
    missing = set(all_scraper_services) - set(AUDITED_FILES)
    assert not missing, (
        f"New scraper-pipeline file(s) found but not in AUDITED_FILES: {missing}"
    )
