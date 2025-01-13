from typing import Callable
from pydantic import BaseModel
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from clients.base import BaseLLMClient
from operations import ActionModel, ACTIONS, UnknownOperation


class DialogProcessError(Exception):
    pass


class BaseDialog:
    actions = ACTIONS

    def __init__(self, client: BaseLLMClient) -> None:
        self.client = client
        self.action_data: dict = {}
        self.action_cls: type[ActionModel] = UnknownOperation

    async def process(self, request: AliceRequest, reply: AliceResponse):
        if reply.session_state is None:
            reply.session_state = {}

        request_session = {}
        if request.state and request.state.session:
            if isinstance(request.state.session, BaseModel):
                request_session = request.state.session.model_dump()
            else:
                request_session = request.state.session

        self.action_data = request_session.get('action', {})
        operation: str | None = self.action_data.get('operation')
        if operation and operation not in self.actions:
            raise DialogProcessError(f'Операция {operation} не найдена')
        self.action_cls = self.actions[operation]

        stage: str = request_session.get('stage') or 'begin'
        stage_method = getattr(self, stage, None)
        next_stage: Callable | None = None

        for _ in range(100):
            try:
                if not stage_method:
                    raise DialogProcessError(f'Шаг диалога {stage} не найден')
                if hasattr(stage_method, '__self__'):
                    next_stage = await stage_method(request, reply, None)
                else:
                    next_stage = await stage_method(self, request, reply, None)
            except DialogProcessError as e:
                reply.response.text = str(e)
                reply.response.end_session = True
                break
            except Exception as e:
                reply.response.text = 'Что-то пошло не так'
                reply.response.end_session = True
                break
            if next_stage is None:
                break
            if stage_method.__qualname__ == next_stage.__qualname__:
                break
            stage_method = next_stage

        if stage_method:
            reply.session_state['stage'] = stage_method.__qualname__.split(
                '.'
            )[-1]
        if self.action_data:
            self.action_data['operation'] = self.action_cls.operation
            reply.session_state['action'] = self.action_data

    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        raise NotImplementedError()
