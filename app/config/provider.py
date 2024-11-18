from environs import Env
from pydantic import BaseModel


class RedisInfo(BaseModel):
    host: str
    port: int
    db: int


class DbInfo(BaseModel):
    username: str
    password: str
    host: str
    port: int = 5432
    db_name: str

    def get_connection_str(self):
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}"


class Config(BaseModel):
    token: str
    redis_info: RedisInfo
    db_info: DbInfo


def get_config(env_path: str | None = None) -> Config:
    env = Env()
    env.read_env(env_path)

    return Config(
        token=env('BOT_TOKEN'),
        redis_info=RedisInfo(
            host=env('REDIS_HOST'),
            port=env('REDIS_PORT'),
            db=env('REDIS_DB')
        ),
        db_info=DbInfo(
            username=env('POSTGRES_USER'),
            password=env('POSTGRES_PASSWORD'),
            host=env('POSTGRES_HOST'),
            port=env('POSTGRES_PORT'),
            db_name=env('POSTGRES_DB_NAME'),
        )
    )


config = get_config()
