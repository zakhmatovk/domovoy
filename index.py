import json
from logging import getLogger
from typing import Literal, TypedDict

from pydantic import BaseModel
from migrate import apply_migrations
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.ya_gpt import client

log = getLogger()

CLASSIFY_PROMT = '''
Нужно классифицировать запрос `operation` и выделить сущность `entity` из запроса

классы запросов: ["out_of_stock", "add_stock" ,"task"]

примеры:
"Кончилась паста" - {"operation": "out_of_stock" , "entity": "паста"}
"Добавь таблетки для посудомойки в список покупок" - {"operation": "out_of_stock" , "entity": "таблетки для посудомоечной машины"}
"Я купил капсулы для стиралки" - {"operation": "add_stock" , "entity": "капсулы для стиральной машины"}

Дай ответ в формате json

'''


class RecognizedOperation(BaseModel):
    operation: Literal['out_of_stock', 'add_stock', 'task']
    entity: str

    def message(self):
        if self.operation == 'out_of_stock':
            return f'Я так понимаю, что {self.entity} больше нет'
        if self.operation == 'add_stock':
            return f'Запас {self.entity} пополнен'
        return 'Это что-то новенькое'


class Event(TypedDict):
    body: str | None
    version: str
    session: str


async def process(request: AliceRequest, reply: AliceResponse):
    r = await client.req(CLASSIFY_PROMT, request.request.original_utterance)
    text = None
    for it in r['result']['alternatives']:
        if it['status'] == 'ALTERNATIVE_STATUS_FINAL':
            text = it['message']['text']
    if text is None:
        return None

    operation = RecognizedOperation.model_validate_json(text.strip('`'))
    reply.response.text = operation.message()
    reply.response.end_session = True


async def handler(event: Event, context):
    body = json.loads(event.get('body') or '{}')
    log.warning(json.dumps(body))

    if body.get('method') == 'apply_migrations':
        try:
            await apply_migrations()
            return {'statusCode': 200}
        except Exception as e:
            return {'statusCode': 500, 'body': {'exception': str(e)}}

    alice_request = AliceRequest.model_validate(event)
    reply = AliceResponse()

    try:
        await process(alice_request, reply)
    except Exception as e:
        log.exception(e)
        reply.response.text = 'Во время обработки запроса что-то пошло не так'
        reply.response.end_session = True

    return reply.model_dump()
