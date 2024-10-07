import json
from logging import getLogger
from typing import TypedDict

from migrate import apply_migrations
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse

from dialogs.general import GeneralDialog

log = getLogger()


class Event(TypedDict):
    body: str | None
    version: str
    session: str


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
        await GeneralDialog().process(alice_request, reply)
    except Exception as e:
        log.exception(e)
        reply.response.text = 'Во время обработки запроса что-то пошло не так'
        reply.response.end_session = True

    return reply.model_dump()
