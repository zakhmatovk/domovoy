from typing import Self
from pydantic import BaseModel
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.base import BaseLLMClient
from clients.ya_gpt import client
from dialogs.base import BaseDialog
from operations import ActionModel, ACTIONS

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
    async def process(cls, client: BaseLLMClient, text: str) -> Self:
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
"Кончилась паста" - {"operation": "out_of_stock" }
"Добавь таблетки для посудомойки в список покупок" - {"operation": "buy_list"}
"Я купил капсулы для стиралки" - {"operation": "add_stock" }
"Я купил две пачки капсулы для стиралки по 40 штук" - {"operation": "add_stock"}

В ответе должен быть только json
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
    decision: str | None

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
            self.client,
            request.request.original_utterance,
        )

        if operation.operation not in ACTIONS:
            reply.response.text = (
                f'Не знаю такую операцию {operation.operation}'
            )
            reply.response.end_session = True
            return

        self.action_cls = ACTIONS[operation.operation]
        self.action_data = {
            'operation': operation.operation,
            'entity': None,
        }

        return IncomingDialog.recognize_entity

    async def recognize_entity(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel,
    ):
        fields_set = set(f for f in self.action_cls.model_fields)
        if 'entity' not in fields_set:
            return IncomingDialog.recognize_count

        if 'entity' not in self.action_data:
            return IncomingDialog.recognize_count

        entity = await RecognizedEntity.process(
            self.client,
            request.request.original_utterance,
        )
        self.action_data['entity'] = entity.entity

        return IncomingDialog.recognize_count

    async def recognize_count(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel,
    ):
        fields_set = set(f for f in self.action_cls.model_fields)
        if 'count' not in fields_set:
            return IncomingDialog.done
        if 'count' not in self.action_data:
            return IncomingDialog.done

        count = await RecognizeCount.process(
            self.client,
            request.request.original_utterance,
        )
        if count.count is not None:
            self.action_data['count'] = count.count
        if count.additional_question is not None:
            reply.response.text = count.additional_question
            return 'recognize_count'
        return IncomingDialog.done

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        action = self.action_cls.model_validate(self.action_data)
        reply.response.text = action.complete_phrase()
        reply.response.end_session = True
        return None
