from decimal import Decimal
from uuid import uuid4
from typing import Any
from alice_types.request import AliceRequest


class Dataset:

    @classmethod
    async def alice_request(cls, **kw: dict[str, Any]) -> AliceRequest:
        from alice_types.request.meta import Meta
        from alice_types.request.session import Application, Session
        from alice_types.request.type.simple import RequestSimpleUtterance

        client_id = str(uuid4())
        session_id = str(uuid4())
        skill_id = str(uuid4())
        application_id = str(uuid4())
        version = str(uuid4())

        return AliceRequest(
            meta=Meta(
                locale='ru_RU',
                timezone='UTC',
                client_id=client_id,
            ),
            request=RequestSimpleUtterance(
                original_utterance='Закончилась паста', type='SimpleUtterance'
            ),
            session=Session(
                message_id=Decimal(0),
                session_id=session_id,
                new=True,
                skill_id=skill_id,
                user=None,
                application=Application(application_id=application_id),
            ),
            state=None,
            version=version,
            account_linking_complete_event=None,
        )
