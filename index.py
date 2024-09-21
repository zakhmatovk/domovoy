import json
from logging import getLogger
from typing import TypedDict
from migrate import apply_migrations

log = getLogger()


class Event(TypedDict):
    body: str | None
    version: str
    session: str


async def handler(event: Event, context):
    body = json.loads(event.get('body') or '{}')

    if body.get('method') == 'apply_migrations':
        try:
            await apply_migrations()
            return {'statusCode': 200}
        except Exception as e:
            return {'statusCode': 500, 'body': {'exception': str(e)}}
    # Execute query with the retry_operation helper.
    log.warning(json.dumps(body))
    return {
        "version": event["version"],
        "session": event["session"],
        "response": {"text": 'Пытаюсь понять ответ', "end_session": True},
    }
