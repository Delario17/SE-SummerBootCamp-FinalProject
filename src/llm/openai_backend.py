"""OpenAI-compatible LLM backend using the openai SDK."""
import json
from openai import AsyncOpenAI
from src.models import Message, ToolCall, LLMResponse


class OpenAICompatBackend:
    """LLM backend that communicates with an OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        api_base: str = "https://api.openai.com/v1",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
        )

    async def chat(
        self, messages: list[Message], tools: list[dict]
    ) -> LLMResponse:
        """Send messages to the LLM and return a response."""
        openai_messages = [self._message_to_dict(m) for m in messages]
        openai_tools = tools if tools else None

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        choice = response.choices[0]
        message = choice.message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def _message_to_dict(self, message: Message) -> dict:
        """Convert a Message to OpenAI-compatible dict format."""
        result: dict = {"role": message.role}

        if message.content is not None:
            result["content"] = message.content

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in message.tool_calls
            ]

        if message.tool_call_id is not None:
            result["tool_call_id"] = message.tool_call_id

        if message.name is not None:
            result["name"] = message.name

        return result