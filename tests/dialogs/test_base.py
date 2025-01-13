from typing import ClassVar
from alice_types.request import AliceRequest, State
from alice_types.response import AliceResponse
from pydantic import BaseModel

from clients.base import BaseLLMClient
from dialogs.base import BaseDialog, DialogProcessError
from operations import ActionModel, UnknownOperation


class TestDialog(BaseDialog):
    def __init__(self, client: BaseLLMClient) -> None:
        super().__init__(client)
        self.stages = list[str]()


class TestHappyDialog(TestDialog):
    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        self.stages.append('begin')
        reply.response.text = 'stage begin'
        return TestHappyDialog.stage_one

    async def stage_one(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('stage_one')
        reply.response.text = 'stage stage_one'
        return TestHappyDialog.stage_two

    async def stage_two(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('stage_two')
        reply.response.text = 'stage stage_two'
        return TestHappyDialog.done

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('done')
        reply.response.text = 'stage done'
        return None


async def test_dialog_stage(dataset, dummy_llm_client):
    alice_request = await dataset.alice_request()
    alice_reply = AliceResponse()
    dialog = TestHappyDialog(dummy_llm_client)
    await dialog.process(alice_request, alice_reply)

    assert dialog.stages == [
        'begin',
        'stage_one',
        'stage_two',
        'done',
    ], 'Зашли не везде'

    assert (
        alice_reply.response.text == 'stage done'
    ), 'Остановились в неправильном шаге'


class TestErrorDialog(TestDialog):

    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        self.stages.append('begin')
        reply.response.text = 'stage begin'
        return TestErrorDialog.stage_one

    async def stage_one(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('stage_one')
        reply.response.text = 'stage stage_one'
        raise ValueError('stage_one error')
        return TestErrorDialog.done

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('done')
        reply.response.text = 'stage done'
        return None


async def test_dialog_stage_default_error(dataset, dummy_llm_client):
    alice_request = await dataset.alice_request()
    alice_reply = AliceResponse()
    dialog = TestErrorDialog(dummy_llm_client)
    await dialog.process(alice_request, alice_reply)

    assert dialog.stages == [
        'begin',
        'stage_one',
    ], 'Зашли не везде'

    assert (
        alice_reply.response.text == 'Что-то пошло не так'
    ), 'Неправильный текст ошибки'
    assert (
        alice_reply.response.end_session == True
    ), 'Конец сессии не установлен'


class TesCustomErrorDialog(TestDialog):
    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        self.stages.append('begin')
        reply.response.text = 'stage begin'
        return TesCustomErrorDialog.stage_one

    async def stage_one(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('stage_one')
        reply.response.text = 'stage stage_one'
        raise DialogProcessError('Кастомная ошибка')
        return TestErrorDialog.done

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('done')
        reply.response.text = 'stage done'
        return None


async def test_dialog_stage_custom_error(dataset, dummy_llm_client):
    alice_request = await dataset.alice_request()
    alice_reply = AliceResponse()
    dialog = TesCustomErrorDialog(dummy_llm_client)
    await dialog.process(alice_request, alice_reply)

    assert dialog.stages == [
        'begin',
        'stage_one',
    ], 'Зашли не везде'

    assert (
        alice_reply.response.text == 'Кастомная ошибка'
    ), 'Неправильный текст ошибки'
    assert (
        alice_reply.response.end_session == True
    ), 'Конец сессии не установлен'


class TestAction(ActionModel):
    operation: ClassVar[str] = 'test_action'
    payload_int: int


class TestAdditionalQuestionDialog(TestDialog):
    actions = {
        None: UnknownOperation,
        'test_action': TestAction,
    }

    def __init__(
        self, client: BaseLLMClient, pass_stage_one: bool = False
    ) -> None:
        super().__init__(client)
        self.pass_stage_one = pass_stage_one

    async def begin(
        self,
        request: AliceRequest,
        reply: AliceResponse,
        action: ActionModel | None = None,
    ):
        self.stages.append('begin')
        reply.response.text = 'stage begin'
        self.action_cls = TestAction
        self.action_data = dict(payload_int=3)
        return TestAdditionalQuestionDialog.stage_one

    async def stage_one(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('stage_one')

        if self.pass_stage_one:
            return TestAdditionalQuestionDialog.done

        reply.response.text = 'Что-то уточняю?'
        return TestAdditionalQuestionDialog.stage_one

    async def done(
        self, request: AliceRequest, reply: AliceResponse, action: ActionModel
    ):
        self.stages.append('done')
        reply.response.text = 'stage done'
        return None


async def test_additional_question(dataset, dummy_llm_client):
    alice_request = await dataset.alice_request()
    alice_reply = AliceResponse()
    dialog = TestAdditionalQuestionDialog(dummy_llm_client)
    await dialog.process(alice_request, alice_reply)

    assert dialog.stages == [
        'begin',
        'stage_one',
    ], 'Зашли не везде'

    assert (
        alice_reply.response.text == 'Что-то уточняю?'
    ), 'Неправильный текст вопроса'
    assert alice_reply.response.end_session != True, 'Неожиданный конец сессии'

    assert (
        alice_reply.session_state.get('stage') == 'stage_one'
    ), 'Остановились в неправильном шаге'
    assert alice_reply.session_state.get('action') == {
        'operation': 'test_action',
        'payload_int': 3,
    }, 'Прикопали неправильный action'


async def test_additional_question_process_again(dataset, dummy_llm_client):
    alice_request = await dataset.alice_request()
    alice_reply = AliceResponse()
    dialog = TestAdditionalQuestionDialog(dummy_llm_client)
    await dialog.process(alice_request, alice_reply)

    assert (
        alice_reply.session_state.get('stage') == 'stage_one'
    ), 'Остановились в неправильном шаге'
    assert alice_reply.session_state.get('action') == {
        'operation': 'test_action',
        'payload_int': 3,
    }, 'Прикопали неправильный action'

    # attach session for second onne
    alice_request_2 = await dataset.alice_request(
        state=State(
            session={
                'stage': 'stage_one',
                'action': {
                    'operation': 'test_action',
                    'payload_int': 3,
                },
            }
        )
    )

    dialog_2 = TestAdditionalQuestionDialog(
        dummy_llm_client, pass_stage_one=True
    )
    alice_reply_2 = AliceResponse()
    await dialog_2.process(alice_request_2, alice_reply_2)

    assert dialog_2.stages == [
        'stage_one',
        'done',
    ], 'Зашли не везде или слишком много куда'
