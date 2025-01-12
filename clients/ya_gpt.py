import os
from typing import Literal, TypedDict

import aiohttp

YA_GPT_KEY = os.environ['YA_GPT_KEY']
FOLDER_ID = 'b1gac1g0nm3qptu01u57'


class NoReply(Exception):
    pass


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
    base_url = (
        'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    )

    def __init__(self) -> None:
        pass

    async def _req(self, json) -> aiohttp.ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.base_url,
                json=json,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Api-Key {YA_GPT_KEY}",
                },
            ) as response:
                response.raise_for_status()
                await response.read()
                return response

    async def req(self, prompt_text: str, message_text: str) -> ResponseGPT:
        promt: RequestGTP = {
            'modelUri': f'gpt://{FOLDER_ID}/yandexgpt-lite/latest',
            'completionOptions': {
                'stream': False,
                'temperature': 0.0,
                'maxTokens': 2000,
            },
            'messages': [
                {'role': 'system', 'text': prompt_text},
                {'role': 'user', 'text': message_text},
            ],
        }
        response = await self._req(promt)
        return await response.json()

    async def req_str(self, prompt_text: str, message_text: str) -> str:
        promt: RequestGTP = {
            'modelUri': f'gpt://{FOLDER_ID}/yandexgpt-lite/latest',
            'completionOptions': {
                'stream': False,
                'temperature': 0.0,
                'maxTokens': 2000,
            },
            'messages': [
                {'role': 'system', 'text': prompt_text},
                {'role': 'user', 'text': message_text},
            ],
        }
        response = await self._req(promt)
        response_data: ResponseGPT = await response.json()

        text = None
        for it in response_data['result']['alternatives']:
            if it['status'] == 'ALTERNATIVE_STATUS_FINAL':
                text = it['message']['text']
        if text is None:
            raise NoReply()
        return text.strip('`')


client = YaGPTClient()
