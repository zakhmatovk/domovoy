import asyncio
import json
import os
from ydb_pool import ydb_pool
from migrate import apply_migrations

# Параметры подключения
YDB_ENDPOINT = os.getenv('YDB_ENDPOINT')
YDB_DATABASE = os.getenv('YDB_DATABASE')
YDB_HAS_CREDENTIALS = os.getenv('YDB_DATABASE', '').capitalize() == 'True'
POOL_SIZE = 5


async def select_one():
    query = 'SELECT 1;'
    try:
        print('request', query)
        r = await ydb_pool.execute(query=query)
        return r
    except Exception as e:
        print(f'An error occurred: {e}')


async def handler(event, context):
    body = json.loads(event.get('body') or '{}')
    if body.get('method') == 'apply_migrations':
        try:
            await apply_migrations()
            return {'statusCode': 200}
        except Exception as e:
            return {'statusCode': 500, 'body': {'exception': str(e)}}
    # Execute query with the retry_operation helper.
    result = await select_one()
    return {
        'statusCode': 200,
        'body': result[0].rows,
    }


# Выполнение функции в асинхронном контексте
if __name__ == '__main__':
    asyncio.run(select_one())
