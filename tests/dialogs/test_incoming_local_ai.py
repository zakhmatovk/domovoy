from alice_types.request import AliceRequest, State
from alice_types.response import AliceResponse
from clients.local_llm import LocalLLMClient
from dialogs.incoming import IncomingDialog


async def test_simple(dataset, external_api):
    client = LocalLLMClient()
    alice_request = await dataset.alice_request(
        original_utterance='Закончилась каша'
    )
    alice_reply = AliceResponse()
    dialog = IncomingDialog(client)
    await dialog.process(alice_request, alice_reply)

    print(alice_reply.response.text)
    print(alice_reply.session_state)
