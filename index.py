import json
from logging import getLogger
from typing import TypedDict
from migrate import apply_migrations
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse

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

    # if alice_request.is_new_session():
    #     reply.response.text = "Привет, скажи что-нибудь и я это повторю"
    # else:
    reply.response.text = alice_request.request.original_utterance

    reply_body = reply.model_dump()
    log.warning(json.dumps(body))
    return reply_body
