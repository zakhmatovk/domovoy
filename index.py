import json
from logging import getLogger
from typing import TypedDict
from migrate import apply_migrations
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.ya_gpt import client

log = getLogger()

CLASSIFY_PROMT = '''
Нужно классифицировать запрос `class` и выделить сущность `entity` из запроса

классы запросов: ["out_of_stock", "add_stock" ,"task"]

примеры:
"Кончилась паста" - {"class": "out_of_stock" , "entity": "паста"}
"Добавь таблетки для посудомойки в список покупок" - {"class": "out_of_stock" , "entity": "таблетки для посудомоечной машины"}
"Я купил капсулы для стиралки" - {"class": "add_stock" , "entity": "капсулы для стиральной машины"}

Дай ответ в формате json

'''


class Event(TypedDict):
    body: str | None
    version: str
    session: str


async def process(request: AliceRequest, reply: AliceResponse):
    r = await client.req(CLASSIFY_PROMT, request.request.original_utterance)
    log.warn(json.dumps(r))


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

    classify_result = await process(alice_request, reply)

    reply.response.text = alice_request.request.original_utterance
    reply.response.end_session = True

    return reply.model_dump()
