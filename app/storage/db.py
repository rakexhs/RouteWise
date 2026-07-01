import os
from collections.abc import Generator
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.config import get_settings
from app.schemas import CostBreakdown, RequestLogItem
from app.storage.models import Base, RequestLog


def _ensure_data_dir() -> None:
    os.makedirs("data", exist_ok=True)


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _ensure_data_dir()
        settings = get_settings()
        url = settings.database_url
        kwargs = {}
        if url.startswith("sqlite"):
            # The default QueuePool caps out at 15 connections; under load the
            # event loop ends up waiting on connections that only blocked
            # requests can release, deadlocking the gateway. SQLite connections
            # are cheap, so skip pooling entirely for file-backed databases.
            # In-memory databases need StaticPool: every new connection to
            # :memory: would otherwise get a fresh, empty database.
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
            kwargs["poolclass"] = StaticPool if ":memory:" in url else NullPool
        _engine = create_engine(url, **kwargs)
        if url.startswith("sqlite") and ":memory:" not in url:
            @event.listens_for(_engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=15000")
                cursor.close()
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def init_db() -> None:
    _ensure_data_dir()
    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def log_request(
    session: Session,
    *,
    trace_id: str,
    model_requested: str,
    model_used: str,
    route_reason: str,
    cache_status: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
    latency_ms: float,
    feature: str | None,
    provider: str,
    redacted_prompt_hash: str,
    error: str | None = None,
) -> RequestLog:
    entry = RequestLog(
        trace_id=trace_id,
        model_requested=model_requested,
        model_used=model_used,
        route_reason=route_reason,
        cache_status=cache_status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
        latency_ms=latency_ms,
        feature=feature,
        provider=provider,
        redacted_prompt_hash=redacted_prompt_hash,
        error=error,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_recent_requests(session: Session, limit: int = 50, offset: int = 0) -> list[RequestLogItem]:
    rows = (
        session.execute(
            select(RequestLog).order_by(RequestLog.timestamp.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return [
        RequestLogItem(
            id=r.id,
            trace_id=r.trace_id,
            timestamp=r.timestamp.isoformat(),
            model_requested=r.model_requested,
            model_used=r.model_used,
            route_reason=r.route_reason,
            cache_status=r.cache_status,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            estimated_cost=r.estimated_cost,
            latency_ms=r.latency_ms,
            feature=r.feature,
            provider=r.provider,
            error=r.error,
        )
        for r in rows
    ]


def get_spend(session: Session, since: datetime) -> float:
    result = session.execute(
        select(func.coalesce(func.sum(RequestLog.estimated_cost), 0.0)).where(
            RequestLog.timestamp >= since
        )
    ).scalar()
    return float(result or 0.0)


def get_cost_breakdown(session: Session, since: datetime) -> list[CostBreakdown]:
    rows = session.execute(
        select(
            RequestLog.model_used,
            RequestLog.feature,
            func.count(RequestLog.id),
            func.sum(RequestLog.estimated_cost),
            func.sum(RequestLog.prompt_tokens + RequestLog.completion_tokens),
        )
        .where(RequestLog.timestamp >= since)
        .group_by(RequestLog.model_used, RequestLog.feature)
    ).all()
    return [
        CostBreakdown(
            model=row[0],
            feature=row[1],
            request_count=int(row[2]),
            total_cost=float(row[3] or 0.0),
            total_tokens=int(row[4] or 0),
        )
        for row in rows
    ]


def get_daily_spend(session: Session) -> float:
    return get_spend(session, datetime.utcnow() - timedelta(days=1))


def get_monthly_spend(session: Session) -> float:
    return get_spend(session, datetime.utcnow() - timedelta(days=30))
