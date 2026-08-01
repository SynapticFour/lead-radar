"""Unit tests for keyword scoring precision."""

from scoring import load_keywords, score_item


KW = load_keywords()


def _item(text, source="hn", **extra):
    base = {
        "text": text,
        "title": text[:80],
        "source": source,
        "points": 0,
        "created_at": None,
    }
    base.update(extra)
    return base


def test_vibe_coding_matches():
    score, reasons = score_item(
        _item("Our vibe coding prototype is unmaintainable — need help"),
        KW,
    )
    assert score >= 4
    assert any("vibe" in r or "intent" in r or "pain" in r for r in reasons)


def test_bare_cursor_mouse_not_a_lead():
    score, _ = score_item(
        _item("How do I change the mouse cursor duplicate icon"),
        KW,
    )
    assert score == 0


def test_bare_hire_without_tool_not_enough():
    score, _ = score_item(_item("We need to hire a developer next quarter"), KW)
    # intent only → below 2-category gate
    assert score == 0


def test_freelancer_game_mess_not_tool():
    score, _ = score_item(
        _item("Looking for a freelancer to fix the mess in my Godot game"),
        KW,
    )
    assert score == 0


def test_security_audit_alone_not_a_lead():
    score, _ = score_item(_item("We scheduled a security audit for Q3"), KW)
    assert score == 0


def test_github_needs_intent_or_pain_tool():
    score, _ = score_item(
        _item("acme/.cursorrules\nA demo with Claude Code notes", source="github"),
        KW,
    )
    # tools only on github → 0
    assert score == 0


def test_threshold_tools_pain_without_boost():
    """tools+pain = 3; digest threshold is 4 without HN/reddit boost."""
    from main import THRESHOLD

    score, _ = score_item(
        _item("Claude Code left us with technical debt everywhere"),
        KW,
    )
    assert score == 3
    assert score < THRESHOLD
