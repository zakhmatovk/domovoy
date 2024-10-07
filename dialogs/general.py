from typing import Literal
from pydantic import BaseModel
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.ya_gpt import client

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


class GeneralDialog:
    async def process(self, request: AliceRequest, reply: AliceResponse):
        r = await client.req(
            CLASSIFY_PROMT, request.request.original_utterance
        )
        text = None
        for it in r['result']['alternatives']:
            if it['status'] == 'ALTERNATIVE_STATUS_FINAL':
                text = it['message']['text']
        if text is None:
            return None

        operation = RecognizedOperation.model_validate_json(text.strip('`'))
        reply.response.text = operation.message()
        reply.response.end_session = True
