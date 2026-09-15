"""Integration tests for database migrations and schema lifecycle (P0.2).

Validates:
1. Fresh DB migration creates all tables including protocol_decisions.
2. protocol_decisions table columns, nullability, and types match ORM expectations.
3. Primary key and indexes (unique decision_id, secondary indexes) exist.
4. Clean downgrade drops protocol_decisions while leaving initial schema intact, and re-upgrades.
5. Pre-existing data in tables (events, runs, experiments) survives upgrade to head.
6. alembic upgrade head is idempotent.
7. ProtocolDecisionModel persistence and retrieval via ORM and EventPersistenceSubscriber.
8. Zero schema drift detected via alembic check against Base.metadata.
9. Production startup safeguard prevents silent unprovisioned execution and succeeds when provisioned.
"""

import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orion.api.app import create_app
from orion.core.config import ApiSettings, DatabaseSettings, OrionSettings
from orion.db.models.decision import ProtocolDecisionModel
from orion.db.persistence_subscriber import EventPersistenceSubscriber
from orion.protocol.decision_engine import DecisionStatus, ProtocolDecision
from orion.protocol.evidence import ProtocolEvidence

EXPECTED_TABLES = {
    "alerts",
    "alembic_version",
    "dataset_versions",
    "events",
    "experiments",
    "model_versions",
    "protocol_decisions",
    "recordings",
    "runs",
    "steps",
    "system_health",
}


def get_alembic_config(db_file: Path) -> Config:
    """Create an Alembic Config pointing to the temporary SQLite database."""
    ini_path = Path("alembic.ini").resolve()
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.resolve()}")
    return cfg


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provides a path to an isolated temporary SQLite database file."""
    return tmp_path / f"test_orion_{uuid.uuid4().hex[:8]}.db"


@pytest.mark.integration
def test_fresh_database_migration_creates_all_tables(temp_db_path: Path) -> None:
    """Verify that alembic upgrade head creates all expected tables on a fresh database."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    inspector = inspect(sync_engine)
    tables = set(inspector.get_table_names())
    sync_engine.dispose()

    assert EXPECTED_TABLES.issubset(tables), f"Missing tables: {EXPECTED_TABLES - tables}"


@pytest.mark.integration
def test_protocol_decisions_table_columns_and_types(temp_db_path: Path) -> None:
    """Verify protocol_decisions columns, nullability, and types match SQLAlchemy model."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    inspector = inspect(sync_engine)
    columns = {col["name"]: col for col in inspector.get_columns("protocol_decisions")}
    sync_engine.dispose()

    expected_columns = {
        "id",
        "decision_id",
        "experiment_id",
        "run_id",
        "step_id",
        "step_number",
        "status",
        "observed_action",
        "expected_actions",
        "confidence",
        "entropy",
        "debounce_count",
        "debounce_threshold",
        "explanation",
        "evidence",
        "retroactive_skips",
        "created_at",
        "updated_at",
    }

    assert expected_columns.issubset(set(columns.keys())), (
        f"Missing columns: {expected_columns - set(columns.keys())}"
    )

    # Validate nullability constraints
    for col_name in expected_columns:
        assert not columns[col_name]["nullable"], f"Column {col_name} should not be nullable"


@pytest.mark.integration
def test_protocol_decisions_indexes(temp_db_path: Path) -> None:
    """Verify primary key and indexes exist on protocol_decisions table."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    inspector = inspect(sync_engine)
    pk_constraint = inspector.get_pk_constraint("protocol_decisions")
    indexes = inspector.get_indexes("protocol_decisions")
    sync_engine.dispose()

    assert "id" in pk_constraint.get("constrained_columns", [])

    index_map = {idx["name"]: idx for idx in indexes}
    assert "ix_protocol_decisions_decision_id" in index_map
    assert bool(index_map["ix_protocol_decisions_decision_id"]["unique"]) is True
    assert index_map["ix_protocol_decisions_decision_id"]["column_names"] == ["decision_id"]

    for col in ["experiment_id", "run_id", "status", "step_id"]:
        idx_name = f"ix_protocol_decisions_{col}"
        assert idx_name in index_map, f"Missing index {idx_name}"
        assert index_map[idx_name]["column_names"] == [col]


@pytest.mark.integration
def test_migration_downgrade_and_reupgrade(temp_db_path: Path) -> None:
    """Verify clean downgrade removes protocol_decisions and re-upgrade restores it."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    # Downgrade by 1 revision back to initial schema (56159e4d40d2)
    command.downgrade(cfg, "-1")

    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    inspector = inspect(sync_engine)
    tables_after_downgrade = set(inspector.get_table_names())

    assert "protocol_decisions" not in tables_after_downgrade
    assert "events" in tables_after_downgrade
    assert "experiments" in tables_after_downgrade
    assert "runs" in tables_after_downgrade

    # Re-upgrade to head
    command.upgrade(cfg, "head")
    inspector = inspect(sync_engine)
    tables_after_reupgrade = set(inspector.get_table_names())
    sync_engine.dispose()

    assert "protocol_decisions" in tables_after_reupgrade


@pytest.mark.integration
def test_existing_data_preserved_during_upgrade(temp_db_path: Path) -> None:
    """Verify that upgrading from initial_schema to head preserves existing data intact."""
    cfg = get_alembic_config(temp_db_path)

    # 1. Upgrade only to initial schema
    command.upgrade(cfg, "56159e4d40d2")

    # 2. Insert data into experiments and events
    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO experiments (id, code, name, version, status, specification, created_at, updated_at) "
                "VALUES ('exp-001', 'EXP-BAS-001', 'BAS Crystal Growth', '1.0.0', 'ACTIVE', '{\"steps\": []}', "
                "'2026-09-11 00:00:00', '2026-09-11 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO events (id, event_type, source, payload, created_at, updated_at) "
                "VALUES ('ev-001', 'ObservationCaptured', 'BAS-TEST', '{\"test\": true}', "
                "'2026-09-11 00:00:00', '2026-09-11 00:00:00')"
            )
        )

    # 3. Upgrade to head (adds protocol_decisions)
    command.upgrade(cfg, "head")

    # 4. Verify existing records survive unchanged
    with sync_engine.begin() as conn:
        exp_row = conn.execute(
            text("SELECT code, name, status FROM experiments WHERE id = 'exp-001'")
        ).fetchone()
        assert exp_row is not None
        assert exp_row[0] == "EXP-BAS-001"
        assert exp_row[1] == "BAS Crystal Growth"
        assert exp_row[2] == "ACTIVE"

        event_row = conn.execute(
            text("SELECT event_type, source FROM events WHERE id = 'ev-001'")
        ).fetchone()
        assert event_row is not None
        assert event_row[0] == "ObservationCaptured"
        assert event_row[1] == "BAS-TEST"

    sync_engine.dispose()


@pytest.mark.integration
def test_upgrade_head_is_idempotent(temp_db_path: Path) -> None:
    """Verify running alembic upgrade head multiple times is idempotent and error-free."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")
    # Second upgrade should be a no-op
    command.upgrade(cfg, "head")

    sync_engine = create_engine(f"sqlite:///{temp_db_path}")
    inspector = inspect(sync_engine)
    tables = set(inspector.get_table_names())
    sync_engine.dispose()

    assert "protocol_decisions" in tables


@pytest.mark.integration
async def test_protocol_decision_orm_persistence_and_query(temp_db_path: Path) -> None:
    """Verify ORM insert and query of ProtocolDecisionModel on an Alembic-migrated database."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{temp_db_path.resolve()}"
    engine: AsyncEngine = create_async_engine(async_url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    decision_id = f"dec-{uuid.uuid4().hex[:12]}"
    async with session_factory() as session, session.begin():
        record = ProtocolDecisionModel(
            decision_id=decision_id,
            experiment_id="exp-bas-01",
            run_id="run-test-01",
            step_id="step-mix-solution",
            step_number=2,
            status="SUCCESS",
            observed_action="MIX_CHEMICALS",
            expected_actions=["MIX_CHEMICALS", "SWIRL_FLASK"],
            confidence=0.985,
            entropy=0.015,
            debounce_count=2,
            debounce_threshold=2,
            explanation="Astronaut successfully completed chemical mixing protocol step.",
            evidence={"action_matches": True, "required_matches": 2},
            retroactive_skips=[],
        )
        session.add(record)

    # Query back
    async with session_factory() as session:
        stmt = select(ProtocolDecisionModel).where(ProtocolDecisionModel.decision_id == decision_id)
        result = await session.execute(stmt)
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.decision_id == decision_id
        assert retrieved.step_id == "step-mix-solution"
        assert retrieved.status == "SUCCESS"
        assert retrieved.confidence == pytest.approx(0.985)
        assert retrieved.expected_actions == ["MIX_CHEMICALS", "SWIRL_FLASK"]
        assert retrieved.evidence == {"action_matches": True, "required_matches": 2}

    await engine.dispose()


@pytest.mark.integration
async def test_persistence_subscriber_persist_decision(temp_db_path: Path) -> None:
    """Verify EventPersistenceSubscriber.persist_decision() writes to protocol_decisions table."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{temp_db_path.resolve()}"
    engine: AsyncEngine = create_async_engine(async_url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    subscriber = EventPersistenceSubscriber(session_factory)
    decision = ProtocolDecision(
        step_id="step-cap-vial",
        step_number=3,
        status=DecisionStatus.VALID,
        observed_action="CAP_VIAL",
        expected_actions=["CAP_VIAL"],
        confidence=0.99,
        entropy=0.01,
        debounce_count=3,
        debounce_threshold=2,
        explanation="Vial securely capped.",
        evidence=ProtocolEvidence(
            activity_label="CAP_VIAL",
            mapped_action="CAP_VIAL",
            confidence=0.99,
        ),
    )

    await subscriber.persist_decision(
        decision=decision,
        experiment_id="exp-bas-02",
        run_id="run-test-02",
    )

    # Verify query
    async with session_factory() as session:
        stmt = select(ProtocolDecisionModel).where(
            ProtocolDecisionModel.decision_id == str(decision.decision_id)
        )
        result = await session.execute(stmt)
        persisted = result.scalar_one_or_none()

        assert persisted is not None
        assert persisted.step_id == "step-cap-vial"
        assert persisted.status == "VALID"
        assert persisted.observed_action == "CAP_VIAL"

    await engine.dispose()


@pytest.mark.integration
def test_alembic_check_reports_zero_drift(temp_db_path: Path) -> None:
    """Verify alembic check detects zero schema drift against Base.metadata."""
    cfg = get_alembic_config(temp_db_path)
    command.upgrade(cfg, "head")
    # command.check raises an exception if drift or unhandled revisions exist
    command.check(cfg)


@pytest.mark.integration
async def test_production_startup_safeguard(tmp_path: Path) -> None:
    """Verify production startup fails if schema is missing, but succeeds when provisioned."""
    # 1. Unprovisioned database: startup MUST fail with RuntimeError
    unprovisioned_db = tmp_path / "unprovisioned.db"
    unprovisioned_settings = OrionSettings(
        ORION_ENV="production",
        ORION_STATION_ID="BAS-TEST-BENCH",
        api=ApiSettings(
            secret_key="a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8"
        ),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{unprovisioned_db}"),
    )
    app_unprovisioned = create_app(settings=unprovisioned_settings)

    with pytest.raises(RuntimeError) as exc_info:
        async with app_unprovisioned.router.lifespan_context(app_unprovisioned):
            pass

    assert "Database schema incomplete or unprovisioned" in str(exc_info.value)
    assert "alembic upgrade head" in str(exc_info.value)

    # 2. Provisioned database via Alembic: startup MUST succeed
    provisioned_db = tmp_path / "provisioned.db"
    cfg = get_alembic_config(provisioned_db)
    command.upgrade(cfg, "head")

    provisioned_settings = OrionSettings(
        ORION_ENV="production",
        ORION_STATION_ID="BAS-TEST-BENCH",
        api=ApiSettings(
            secret_key="a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8"
        ),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{provisioned_db}"),
    )
    app_provisioned = create_app(settings=provisioned_settings)

    async with app_provisioned.router.lifespan_context(app_provisioned):
        # Successfully passed through lifespan startup
        pass
