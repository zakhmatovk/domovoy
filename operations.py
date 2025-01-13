from pydantic import BaseModel
from typing import ClassVar, Protocol


class ActionModel(BaseModel):
    operation: ClassVar[str] = ''

    def complete_phrase(self) -> str:
        raise NotImplementedError()


class UnknownOperation(ActionModel):
    operation: ClassVar[str] = 'unknown'

    def complete_phrase(self) -> str:
        return 'Активность не распознана'


class OutOfStockOperation(ActionModel):
    operation: ClassVar[str] = 'out_of_stock'
    entity: str | None

    def complete_phrase(self) -> str:
        return f'{self.entity} закончилось'


class AddStockOperation(ActionModel):
    operation: ClassVar[str] = 'add_stock'
    entity: str
    count: int | None

    def complete_phrase(self) -> str:
        return f'Принял {self.count} {self.entity}'


class TaskOperation(ActionModel):
    operation: ClassVar[str] = 'task'

    def complete_phrase(self) -> str:
        return 'Задача добавлена'


class BuyListOperation(ActionModel):
    operation: ClassVar[str] = 'buy_list'
    entity: str

    def complete_phrase(self) -> str:
        return f'Добавил {self.entity} в список покупок'


ACTIONS: dict[str | None, type[ActionModel]] = {
    None: UnknownOperation,
    'out_of_stock': OutOfStockOperation,
    'add_stock': AddStockOperation,
    'task': TaskOperation,
    'buy_list': BuyListOperation,
}
