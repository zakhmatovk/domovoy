import asyncio
import datetime
import os
import ydb
from logging import getLogger
from typing import Any, Generator
from pydantic import BaseModel, Field
from ydb_pool import ydb_pool


log = getLogger()

MIGRATIONS_DIR = 'migrations'


# Определение модели Pydantic для валидации данных
class Migration(BaseModel):
    name: str = Field(ydb_type=ydb.PrimitiveType.Utf8)
    'The name of the migration'
    applied_at: datetime.datetime = Field(ydb_default='CurrentUtcDate()')
    'The time when the migration was applied'
    migration_code: str = Field(ydb_type=ydb.PrimitiveType.Utf8)
    'The code of the migration'
    rollback_code: str = Field(ydb_type=ydb.PrimitiveType.Utf8)
    'The code for rolling back the migration'

    async def insert(self):
        ydb_types: dict[str, Any] = {
            k: v.json_schema_extra.get('ydb_type')
            for k, v in self.model_fields.items()
            if v.json_schema_extra and v.json_schema_extra.get('ydb_type')
        }
        ydb_defaults: dict[str, Any] = {
            k: v.json_schema_extra.get('ydb_default')
            for k, v in self.model_fields.items()
            if v.json_schema_extra and v.json_schema_extra.get('ydb_default')
        }

        query_builder = []
        for field, ydb_type in ydb_types.items():
            if ydb_type:
                query_builder.append(f'DECLARE ${field} AS {ydb_type};')

        fields = list(ydb_types) + list(ydb_defaults)
        values = []
        query_parameters = {}
        for field in fields:
            if ydb_default := ydb_defaults.get(field):
                values.append(ydb_default)
                continue
            values.append(f'${field}')
            query_parameters[field] = getattr(self, field)

        query_builder.append(
            f'''
            UPSERT INTO migrations({','.join(fields)})
            VALUES({','.join(values)});
            '''
        )
        # return [k for k, v in self.model_fields.items() if v.field .get("switchable")]
        await ydb_pool.execute('\n'.join(query_builder), **query_parameters)


async def apply_migrations():
    await create_migrations_table()
    stored_migrations = {it.name: it for it in collect_migrations()}
    applied_migrations = {it.name: it for it in await fetch_migrations()}

    old_migration_names = set(applied_migrations.keys()) - set(stored_migrations.keys())
    for migration_name in sorted(list(old_migration_names)):
        await down_migration(applied_migrations[migration_name])

    new_migration_names = set(stored_migrations.keys()) - set(applied_migrations.keys())
    for migration_name in sorted(list(new_migration_names)):
        await up_migration(stored_migrations[migration_name])


async def create_migrations_table():
    await ydb_pool.execute(
        '''
        CREATE TABLE IF NOT EXISTS `migrations` (
            `name` Utf8,
            `applied_at` Datetime NOT NULL,
            `migration_code` Utf8 NOT NULL,
            `rollback_code` Utf8 NOT NULL,
            PRIMARY KEY(`name`)
        )
        '''
    )


def collect_migrations() -> Generator[Migration, Any, None]:
    for root, _, filenames in os.walk(MIGRATIONS_DIR):
        for filename in filenames:
            if filename == 'up.sql':
                yield Migration(
                    name=os.path.basename(root),
                    applied_at=datetime.datetime.now(),
                    migration_code=open(os.path.join(root, 'up.sql')).read(),
                    rollback_code=open(os.path.join(root, 'down.sql')).read(),
                )


async def fetch_migrations():
    # Извлечение данных из таблицы migrations
    results = await ydb_pool.execute('SELECT * FROM migrations')
    return [Migration(**row) for row in results[0].rows]


async def up_migration(migration: Migration):
    log.info('Try to apply migration %s', migration.name)
    await ydb_pool.execute(migration.migration_code)

    await migration.insert()

    log.info('Success apply migration %s', migration.name)


async def down_migration(migration: Migration):
    log.info('Try to rollback migration %s', migration.name)
    await ydb_pool.execute(migration.rollback_code)

    await ydb_pool.execute(
        f'''
        DELETE FROM migrations
        WHERE name = "{migration.name}"u
        ''',
    )
    log.info('Success rollback migration %s', migration.name)


if __name__ == '__main__':
    asyncio.run(apply_migrations())
