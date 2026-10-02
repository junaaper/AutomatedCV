"""Ask a chat model for JSON and validate it with Pydantic.

Deliberately not using provider tool-calling / structured-output APIs: many free models
(e.g. on OpenRouter) don't support them, and plain JSON prompting works identically
across Groq, Gemini, OpenRouter and the offline fake.
"""

import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from app.agent.prompts import json_instructions

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class LLMOutputError(RuntimeError):
    pass


def parse_json_object(text: str) -> dict:
    text = _FENCE.sub("", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


async def invoke_json[T: BaseModel](
    llm: BaseChatModel, system: str, user: str, schema: type[T], *, retries: int = 1
) -> T:
    messages: list[BaseMessage] = [
        SystemMessage(f"{system}\n\n{json_instructions(schema)}"),
        HumanMessage(user),
    ]
    last_error: Exception | None = None
    for _ in range(retries + 1):
        reply = await llm.ainvoke(messages)
        text = str(reply.text)
        try:
            return schema.model_validate(parse_json_object(text))
        except (ValueError, ValidationError) as exc:
            last_error = exc
            # Show the model its own output and the error; small models usually fix it.
            messages += [
                AIMessage(text),
                HumanMessage(f"That was not valid. Error: {str(exc)[:500]}\nReturn only the JSON."),
            ]
    raise LLMOutputError(f"Model did not return valid {schema.__name__}: {last_error}")


async def invoke_text(llm: BaseChatModel, system: str, user: str) -> str:
    reply = await llm.ainvoke([SystemMessage(system), HumanMessage(user)])
    text = str(reply.text)
    return text.strip()
