import json
from typing import Any, Callable, Coroutine, Generator
from uuid import uuid4

from aiohttp import web
from aiohttp.test_utils import TestServer
from h11 import Response
from pydantic import BaseModel
import pytest
from alice_types.request import AliceRequest

from clients.ya_gpt import BaseClient, ResponseGPT
from index import RecognizedOperation
from tests.dataset import Dataset


@pytest.fixture
async def api() -> Generator[
    Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
    Any,
    None,
]:
    from index import handler

    version = str(uuid4())
    session = str(uuid4())

    async def handler_cover(data: dict[str, Any]) -> dict[str, Any]:
        r = await handler(
            {'body': json.dumps(data), 'version': version, 'session': session},
            None,
        )
        return r

    yield handler_cover


@pytest.fixture
async def alice_api() -> Generator[
    Callable[[AliceRequest], Coroutine[Any, Any, dict[str, Any]]],
    Any,
    None,
]:
    from index import handler

    async def handler_cover(r: AliceRequest) -> dict[str, Any]:
        r = await handler(r.model_dump(), None)
        return r

    yield handler_cover


@pytest.fixture
async def dataset() -> Generator[type[Dataset], Any, None]:
    yield Dataset


from contextlib import asynccontextmanager


@pytest.fixture
async def external_api(monkeypatch):
    '''
    Фикстура, чтобы мокать взаимодействия с внешними клиентам
    Пример использования:

    ```
    async def handle(request: web.Request) -> dict | BaseModel | web.Response | RecognizedOperation:
        return {'result': True}

    async with external_api(YaGPTClient, handle):
        ...
    ```
    '''

    @asynccontextmanager
    async def _external_api(client: BaseClient, handle: Callable):
        '''
        Внутри контекстного менеджера поднимаем живой сервер и запросы ходят в него
        '''

        async def external_handle(request: web.Request) -> web.Response:
            response: dict | BaseModel | web.Response | RecognizedOperation = (
                await handle(request)
            )
            if isinstance(response, RecognizedOperation):
                covered_response: ResponseGPT = {
                    'result': {
                        'alternatives': [
                            {
                                'status': 'ALTERNATIVE_STATUS_FINAL',
                                'message': {
                                    'text': response.model_dump_json(),
                                    'role': 'assistant',
                                },
                            }
                        ]
                    }
                }
                return web.Response(
                    status=200,
                    body=json.dumps(covered_response).encode(),
                    content_type='application/json',
                )
            elif isinstance(response, dict):
                return web.Response(
                    status=200,
                    body=json.dumps(response).encode(),
                    content_type='application/json',
                )
            elif isinstance(response, BaseModel):
                return web.Response(
                    status=200,
                    body=response.model_dump_json().encode(),
                    content_type='application/json',
                )
            return response

        app = web.Application()
        app.add_routes([web.post('/', external_handle)])
        server = TestServer(app, port=7654)
        await server.start_server()

        monkeypatch.setattr(
            client, 'base_url', f'http://{server.host}:{server.port}/'
        )
        try:
            yield client
        finally:
            monkeypatch.context()
            await server.close()

    yield _external_api
