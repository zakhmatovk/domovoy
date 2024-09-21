import os
from typing import Literal, TypedDict

import aiohttp

YA_GPT_API_TOKEN = os.environ['YA_GPT_API_TOKEN']
FOLDER_ID = 'b1gac1g0nm3qptu01u57'


class CompletionOptions(TypedDict):
    stream: bool
    temperature: float
    maxTokens: int


class MessageGPT(TypedDict):
    role: Literal['system', 'user', 'assistant']
    text: str


class RequestGTP(TypedDict):
    modelUri: str
    completionOptions: CompletionOptions
    messages: list[MessageGPT]


class ResponseAlternativeGPT(TypedDict):
    message: MessageGPT
    status: str


class ResponseResultGPT(TypedDict):
    alternatives: list[ResponseAlternativeGPT]


class ResponseGPT(TypedDict):
    result: ResponseResultGPT


class YaGPTClient:
    base_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

    def __init__(self) -> None:
        pass

    async def req(self, promt_text: str, message_text: str) -> ResponseGPT:
        promt: RequestGTP = {
            'modelUri': f'gpt://{FOLDER_ID}/yandexgpt-lite/latest',
            'completionOptions': {'stream': False, 'temperature': 0.0, 'maxTokens': 2000},
            'messages': [{'role': 'system', 'text': promt_text}, {'role': 'user', 'text': message_text}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.base_url,
                json=promt,
                headers={"Content-Type": "application/json", "Authorization": f"Api-Key {YA_GPT_API_TOKEN}"},
            ) as response:
                response.raise_for_status()
                return await response.json()


client = YaGPTClient()
