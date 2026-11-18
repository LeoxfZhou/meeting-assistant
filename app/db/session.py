from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def build_engine(url: str) -> Engine:
    # 不输出 SQL 参数，避免会议正文进入数据库错误日志。
    return create_engine(url, pool_pre_ping=True, hide_parameters=True,
                         connect_args={"connect_timeout": 5})


def get_session(request: Request) -> Iterator[Session]:
    # 每个请求独立 Session；路由提交写事务，异常和请求结束都会释放连接。
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
