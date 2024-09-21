from logging import getLogger
import os
import ydb.aio
from ydb.convert import ResultSet

log = getLogger()

# Параметры подключения
YDB_ENDPOINT = os.getenv('YDB_ENDPOINT')
YDB_DATABASE = os.getenv('YDB_DATABASE')
YDB_HAS_CREDENTIALS = os.getenv('YDB_DATABASE', '').capitalize() == 'True'
POOL_SIZE = 5


class YdbPool:
    def __init__(self) -> None:
        self.driver = None
        self.driver_config = ydb.DriverConfig(
            endpoint=YDB_ENDPOINT,
            database=YDB_DATABASE,
            credentials=ydb.iam.MetadataUrlCredentials() if YDB_HAS_CREDENTIALS else None,
        )

    async def _get_driver(self):
        if self.driver is None:
            self.driver = ydb.aio.Driver(self.driver_config)
            await self.driver.wait(timeout=5, fail_fast=True)
        return self.driver

    async def execute_old(self, query: str) -> list[ResultSet]:
        driver = await self._get_driver()
        async with ydb.aio.SessionPool(driver, size=POOL_SIZE) as pool:
            async with pool.checkout() as session:
                return await session.transaction(ydb.SerializableReadWrite()).execute(query)

    async def execute(self, query: str, **kw) -> list[ResultSet]:
        driver = await self._get_driver()
        async with ydb.aio.QuerySessionPool(driver) as pool:
            try:
                return await pool.execute_with_retries(query, {f'${k}': v for k, v in kw.items()})
            except Exception as e:
                log.warning('Failed to process migration. %s, %s', str(e), query)
                raise

    async def execute_migration(self, query: str) -> list[ResultSet]:
        driver = await self._get_driver()
        async with ydb.aio.QuerySessionPool(driver) as pool:
            try:
                return await pool.execute_with_retries(query)
            except Exception as e:
                log.warning('Failed to process migration. %s, %s', str(e), query)
                raise


ydb_pool = YdbPool()
