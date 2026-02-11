"""OpenAIClient adapter using strict JSON schema output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

STRICT_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "name": "message_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["classification", "description", "amount_cents", "reason_code"],
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["valid", "invalid", "ignored"],
            },
            "description": {
                "type": ["string", "null"],
            },
            "amount_cents": {
                "type": ["integer", "null"],
            },
            "reason_code": {
                "type": ["string", "null"],
            },
            "reason_message": {
                "type": ["string", "null"],
            },
            "is_refund_keyword": {
                "type": "boolean",
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class MessageClassification:
    """Structured classification result returned by the LLM adapter."""

    classification: str
    description: str | None
    amount_cents: int | None
    reason_code: str | None
    reason_message: str | None
    is_refund_keyword: bool


class OpenAIClient(Protocol):
    """Minimum client protocol expected by the adapter."""

    def responses_create(self, **kwargs: Any) -> dict[str, Any]:
        """Call OpenAI Responses API and return payload as dict."""


class OpenAIMessageClassifier:
    """Classifies messages with strict JSON schema responses."""

    def __init__(
        self,
        client: OpenAIClient,
        *,
        model: str,
        prompt_version: str,
        schema_version: str,
    ) -> None:
        self._client = client
        self._model = model
        self._prompt_version = prompt_version
        self._schema_version = schema_version

    def classify_message(
        self, message_text: str, author_external_id: str
    ) -> MessageClassification:
        """Classify a single message and return normalized result."""
        prompt = (
            "Classify the message as valid, invalid, or ignored for shared purchases. "
            "Extract normalized description and amount in BRL cents when available."
        )
        response = self._client.responses_create(
            model=self._model,
            temperature=0,
            metadata={
                "prompt_version": self._prompt_version,
                "schema_version": self._schema_version,
                "author_external_id": author_external_id,
            },
            input=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": message_text,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": STRICT_CLASSIFICATION_SCHEMA,
            },
        )
        payload = self._extract_payload(response)
        return MessageClassification(
            classification=str(payload.get("classification", "invalid")),
            description=self._optional_string(payload.get("description")),
            amount_cents=self._optional_int(payload.get("amount_cents")),
            reason_code=self._optional_string(payload.get("reason_code")),
            reason_message=self._optional_string(payload.get("reason_message")),
            is_refund_keyword=bool(payload.get("is_refund_keyword", False)),
        )

    def _extract_payload(self, response: dict[str, Any]) -> dict[str, Any]:
        output = response.get("output")
        if not isinstance(output, list) or not output:
            raise ValueError("OpenAI response does not contain output items")

        first_item = output[0]
        if not isinstance(first_item, dict):
            raise ValueError("OpenAI output item has invalid format")

        content = first_item.get("content")
        if not isinstance(content, list) or not content:
            raise ValueError("OpenAI output does not contain content")

        content_item = content[0]
        if not isinstance(content_item, dict):
            raise ValueError("OpenAI content item has invalid format")

        parsed = content_item.get("parsed")
        if isinstance(parsed, dict):
            return parsed

        raise ValueError("OpenAI response does not contain parsed JSON schema output")

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) else None
