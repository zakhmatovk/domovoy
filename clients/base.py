from typing import Protocol


class BaseLLMClient(Protocol):
    # async def req(self, prompt_text: str, message_text: str) -> ResponseGPT: ...

    async def req_str(self, prompt_text: str, message_text: str) -> str: ...
