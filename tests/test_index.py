from aiohttp import web
from clients.ya_gpt import ResponseGPT, YaGPTClient
from index import RecognizedOperation


async def test_apply_migrations(api):
    r = await api({'method': 'apply_migrations'})
    assert r['statusCode'] == 200, 'Миграции не накатились'


async def test_alice_request(alice_api, dataset, external_api):
    async def handle(request: web.Request) -> RecognizedOperation:
        return RecognizedOperation(
            operation='out_of_stock',
            entity='паста',
        )

    alice_request = await dataset.alice_request()

    async with external_api(YaGPTClient, handle):
        response = await alice_api(alice_request)

    assert (
        response['response']['text'] == 'Я так понимаю, что паста больше нет'
    )
