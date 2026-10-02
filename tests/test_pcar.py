import sys
import types

import pytest

from eddy import pcar
from eddy.pcar import PlanError, SupportPlan

PLAN = SupportPlan(
    problem="Missing coursework deadlines.",
    causes=["Reading load is too high."],
    actions=["Provide printed notes before each lesson."],
    result="Coursework is handed in on time.",
)


class FakeResponse:
    def __init__(self, parsed_output, stop_reason="end_turn"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


def fake_anthropic(monkeypatch, *, response=None, error=None):
    """Swap the real SDK for a stand-in, and record what the app sends to it."""
    calls = []

    class APIStatusError(Exception):
        pass

    class RateLimitError(APIStatusError):
        pass

    class APIConnectionError(Exception):
        pass

    class Messages:
        def parse(self, **kwargs):
            calls.append(kwargs)
            if error:
                raise {
                    "rate": RateLimitError,
                    "status": APIStatusError,
                    "network": APIConnectionError,
                }[error]()
            return response

    module = types.SimpleNamespace(
        Anthropic=lambda: types.SimpleNamespace(messages=Messages()),
        APIStatusError=APIStatusError,
        RateLimitError=RateLimitError,
        APIConnectionError=APIConnectionError,
    )
    monkeypatch.setitem(sys.modules, "anthropic", module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return calls


def test_demo_mode_when_no_key_is_set(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    plan, source = pcar.generate_plan("Dyslexia.", "Falling behind. Missed two deadlines.")
    assert source == "demo"
    assert plan.problem == "The student is having difficulty with: Falling behind"
    assert len(plan.causes) >= 3 and len(plan.actions) >= 3


def test_ai_plan_is_returned_and_labelled(monkeypatch):
    calls = fake_anthropic(monkeypatch, response=FakeResponse(PLAN))
    plan, source = pcar.generate_plan("Dyslexia.", "Falling behind.")
    assert (plan, source) == (PLAN, "ai")

    request = calls[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["output_format"] is SupportPlan
    assert "PCAR" in request["system"]
    # What staff typed goes in the user message, kept apart from the instructions.
    assert request["messages"][0]["content"] == (
        "<needs>\nDyslexia.\n</needs>\n\n<problem>\nFalling behind.\n</problem>"
    )
    assert "Dyslexia" not in request["system"]


@pytest.mark.parametrize(
    ("error", "message"),
    [("rate", "busy"), ("status", "returned an error"), ("network", "Could not reach")],
)
def test_ai_errors_become_friendly_messages(monkeypatch, error, message):
    fake_anthropic(monkeypatch, error=error)
    with pytest.raises(PlanError, match=message):
        pcar.generate_plan("needs", "problem")


def test_refusal_is_reported(monkeypatch):
    fake_anthropic(monkeypatch, response=FakeResponse(None, stop_reason="refusal"))
    with pytest.raises(PlanError, match="could not produce a plan"):
        pcar.generate_plan("needs", "problem")


def test_incomplete_plan_is_rejected(monkeypatch):
    empty = PLAN.model_copy(update={"actions": []})
    fake_anthropic(monkeypatch, response=FakeResponse(empty))
    with pytest.raises(PlanError, match="incomplete"):
        pcar.generate_plan("needs", "problem")


def test_failed_generation_saves_nothing_and_keeps_the_form(app, sam, monkeypatch):
    fake_anthropic(monkeypatch, error="rate")
    response = sam.post(
        "/new", {"student_ref": "JS-07", "needs": "Some needs", "problem": "A problem"}
    )
    page = response.get_data(as_text=True)
    assert "The AI service is busy." in page
    assert "Some needs" in page
    assert "JS-07" not in sam.get("/").get_data(as_text=True)


def test_ai_report_is_saved_and_labelled_as_a_draft(app, sam, monkeypatch):
    fake_anthropic(monkeypatch, response=FakeResponse(PLAN))
    response = sam.post(
        "/new", {"student_ref": "JS-07", "needs": "n", "problem": "p"}, follow_redirects=True
    )
    page = response.get_data(as_text=True)
    assert "Provide printed notes before each lesson." in page
    assert "drafted by AI as a starting point" in page
