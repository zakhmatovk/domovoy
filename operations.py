from pydantic import BaseModel
from typing import ClassVar, Protocol


class ActionModel(Protocol):
    def complete_phrase(self) -> str:
        raise NotImplementedError()


class ActionWithEntity(ActionModel):
    entity: str


class ActionWithCount(ActionModel):
    count: int | None


class OutOfStockOperation(BaseModel):
    operation: ClassVar[str] = 'out_of_stock'
    entity: str

    def complete_phrase(self) -> str:
        return f'{self.entity} закончилось'


class AddStockOperation(BaseModel):
    operation: ClassVar[str] = 'add_stock'
    entity: str
    count: int | None

    def complete_phrase(self) -> str:
        return f'Принял {self.count} {self.entity}'


class TaskOperation(BaseModel):
    operation: ClassVar[str] = 'task'

    def complete_phrase(self) -> str:
        return 'Задача добавлена'


class BuyListOperation(ActionModel):
    operation: ClassVar[str] = 'buy_list'
    entity: str

    def complete_phrase(self) -> str:
        return f'Добавил {self.entity} в список покупок'


ACTIONS: dict[str, type[BaseModel]] = {
    'out_of_stock': OutOfStockOperation,
    'add_stock': AddStockOperation,
    'task': TaskOperation,
    'buy_list': BuyListOperation,
}
