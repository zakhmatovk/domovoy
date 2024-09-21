from clients.ya_gpt import ResponseGPT, YaGPTClient
from index import RecognizedOperation


async def test_apply_migrations(api):
    r = await api({'method': 'apply_migrations'})
    assert r['statusCode'] == 200, 'Миграции не накатились'


async def test_alice_request(alice_api, dataset, external_api):
    async def handle(request) -> ResponseGPT:
        recgnize_result = RecognizedOperation(
            operation='out_of_stock',
            entity='паста',
        )

        return {
            'result': {
                'alternatives': [
                    {
                        'status': 'ALTERNATIVE_STATUS_FINAL',
                        'message': {
                            'text': recgnize_result.model_dump_json(),
                            'role': 'assistant',
                        },
                    }
                ]
            }
        }

    alice_request = await dataset.alice_request()

    async with external_api(YaGPTClient, handle):
        response = await alice_api(alice_request)

    assert (
        response['response']['text'] == 'Я так понимаю, что паста больше нет'
    )
