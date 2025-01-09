from typing import Callable
from pydantic import BaseModel
from alice_types.request import AliceRequest
from alice_types.response import AliceResponse
from operations import ActionModel, ACTIONS


class DialogProcessError(Exception):
    pass


class BaseDialog:
    actions = ACTIONS

    def __init__(self) -> None:
        self.action: BaseModel | None = None

    async def process(self, request: AliceRequest, reply: AliceResponse):
        if reply.session_state is None:
            reply.session_state = {}

        request_session = {}
        if request.state and request.state.session:
            if isinstance(request.state.session, BaseModel):
                request_session = request.state.session.model_dump()
            else:
                request_session = request.state.session

        action_data = request_session.get('action', {})
        action_cls = self.actions.get(action_data.get('operation'))
        if action_cls:
            self.action = action_cls.model_validate(action_data)

        stage: str = request_session.get('stage') or 'begin'
        stage_method = getattr(self, stage, None)
        next_stage: Callable | None = None

        for _ in range(100):
            try:
                if not stage_method:
                    raise DialogProcessError(f'Шаг диалога {stage} не найден')
                if hasattr(stage_method, '__self__'):
                    next_stage = await stage_method(
                        request, reply, self.action
                    )
                else:
                    next_stage = await stage_method(
                        self, request, reply, self.action
                    )
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
        if self.action:
            reply.session_state['action'] = self.action.model_dump()

    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        raise NotImplementedError()
