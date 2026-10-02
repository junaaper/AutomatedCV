"""Replays recorded LLM responses, keyed by agent task.

Used by demo mode (so recruiters can click through even if the LLM API is down) and by
the eval suite's offline mode. Responses are recorded with scripts/record_demo.py or
`evals/run_evals.py --record`.
"""

import json
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_INPUT = re.compile(r"<input>\s*(.*?)\s*</input>", re.DOTALL)


class MissingRecording(LookupError):
    pass


def task_of(messages: list[BaseMessage]) -> str:
    return str(messages[0].content).split("\n", 1)[0].removeprefix("TASK:").strip()


def input_of(messages: list[BaseMessage]) -> dict:
    for msg in messages:
        if m := _INPUT.search(str(msg.content)):
            return json.loads(m.group(1))
    return {}


def feedback_key(feedback: str | None) -> str:
    return " ".join((feedback or "").lower().split())


def recording_key(messages: list[BaseMessage]) -> str:
    """'score_fit', or 'draft_cover_letter' / 'draft_cover_letter:<feedback>' for revisions."""
    task = task_of(messages)
    if task == "draft_cover_letter":
        fb = feedback_key(input_of(messages).get("feedback"))
        return f"{task}:{fb}" if fb else task
    return task


class ReplayChatModel(BaseChatModel):
    responses: dict[str, str]
    # Used when there's no recording (e.g. free-text revision feedback in the demo).
    fallback: Any = None

    @property
    def _llm_type(self) -> str:
        return "replay"

    def covers(self, messages: list[BaseMessage]) -> bool:
        return recording_key(messages) in self.responses

    def _lookup(self, messages: list[BaseMessage]) -> ChatResult | None:
        text = self.responses.get(recording_key(messages))
        if text is None:
            return None
        return ChatResult(generations=[ChatGeneration(message=AIMessage(text))])

    def _generate(self, messages, stop=None, run_manager=None, **kw):
        if (result := self._lookup(messages)) is not None:
            return result
        if self.fallback is None:
            raise MissingRecording(recording_key(messages))
        return ChatResult(generations=[ChatGeneration(message=self.fallback.invoke(messages))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kw):
        if (result := self._lookup(messages)) is not None:
            return result
        if self.fallback is None:
            raise MissingRecording(recording_key(messages))
        reply = await self.fallback.ainvoke(messages)
        return ChatResult(generations=[ChatGeneration(message=reply)])


class RecordingChatModel(BaseChatModel):
    """Wraps a real model and keeps each response under its recording key."""

    inner: Any
    recorded: dict[str, str] = {}

    @property
    def _llm_type(self) -> str:
        return "recording"

    def _generate(self, messages, stop=None, run_manager=None, **kw):
        raise NotImplementedError("use the async API")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kw):
        reply = await self.inner.ainvoke(messages)
        # A retry (invalid JSON first time) overwrites, so the stored response is the good one.
        self.recorded[recording_key(messages)] = str(reply.text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(str(reply.text)))])
