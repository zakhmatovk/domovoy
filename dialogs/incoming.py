import re
from typing import Literal, Self
from pydantic import BaseModel
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.ya_gpt import client
from dialogs.base import BaseDialog
from operations import ActionModel, ActionWithEntity, ActionWithCount, ACTIONS

CLASSES = [
    'out_of_stock',
    'add_stock',
    'task',
    'buy_list',
]


class RecognizedBase(BaseModel):
    @classmethod
    def promt(cls) -> str:
        return ''

    @classmethod
    async def process(cls, text: str) -> Self:
        text = await client.req_str(cls.promt(), text)
        return cls.model_validate_json(text)


class RecognizedOperation(RecognizedBase):
    operation: str

    @classmethod
    def promt(cls) -> str:
        return '''
Нужно классифицировать запрос `operation` из списка:
- out_of_stock
- add_stock
- task
- buy_list

Примеры:
"Кончилась паста" - {"class": "out_of_stock" }
"Добавь таблетки для посудомойки в список покупок" - {"class": "buy_list"}
"Я купил капсулы для стиралки" - {"class": "add_stock" }
"Я купил две пачки капсулы для стиралки по 40 штук" - {"class": "add_stock"}

Дай ответ в формате json
'''


class RecognizedEntity(RecognizedBase):
    entity: str

    @classmethod
    def promt(cls) -> str:
        return '''
Распознай сущность из сообщения и положи его в `entity`.

Примеры:
"Кончилась паста" - {"entity": "паста"}
"Добавь таблетки для посудомойки в список покупок" - {"entity": "таблетки для посудомоечной машины"}
"Я купил капсулы для стиралки" - {"entity": "капсулы для стиральной машины""}
"Я купил две пачки капсулы для стиралки по 40 штук" - {"entity": "капсулы для стиральной машины"}
'''


class RecognizeCount(RecognizedBase):
    count: int | None
    additional_question: str | None
    decision: str

    @classmethod
    def promt(cls) -> str:
        return '''
Извлеки количество предметов из сообщения и положить его в "count". 
Если в сообщении нет конкретного количества, то обязательно добавь в ответ запрос на уточнение количества "correction_request".
Объясни почему ты принял такое решение и положил в "decision".

Примеры:
"Я купил капсулы для стиралки" - {"additional_question": "Сколько капсул ты купил?"}
"Я купил пачку капсул для стиралки" - {"additional_question": "Сколько капсул в пачке?"}
"Я купил две пачки капсулы для стиралки по сорок штук" - {"count": 80}
"Одну упаковку с десятью печеньями и ещё одну с пятнадцатью" - {"count": 25}
'''


class DialogProcessError(Exception):
    pass


class IncomingDialog(BaseDialog):
    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        operation = await RecognizedOperation.process(
            request.request.original_utterance
        )
        if operation.operation in ACTIONS:
            reply.response.text = (
                f'Не знаю такую операцию {operation.operation}'
            )
            reply.response.end_session = True
            return

        operation_cls = ACTIONS[operation.operation]
        self.action = operation_cls(operation=operation.operation)

        return IncomingDialog.recognize_entity

    async def recognize_entity(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionWithEntity,
    ):
        if not hasattr(action, 'entity'):
            return IncomingDialog.recognize_count

        if action.entity is not None:
            return IncomingDialog.recognize_count

        entity = await RecognizedEntity.process(
            request.request.original_utterance
        )
        action.entity = entity.entity

        return IncomingDialog.recognize_count

    async def recognize_count(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionWithCount,
    ):
        if not hasattr(action, 'count'):
            return 'done'
        if action.count is not None:
            return 'done'

        count = await RecognizeCount.process(
            request.request.original_utterance
        )
        if count.count is not None:
            action.count = count.count
        if count.additional_question is not None:
            reply.response.text = count.additional_question
            return 'recognize_count'
        return IncomingDialog.done

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        reply.response.text = action.complete_phrase()
        reply.response.end_session = True
        return None
