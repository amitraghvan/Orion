"""Integration tests for database session transactions and rollbacks."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_session_execute_and_rollback(test_session: AsyncSession) -> None:
    """Verify async session can execute raw queries and rollback cleanly."""
    result = await test_session.execute(text("SELECT 1"))
    val = result.scalar()
    assert val == 1
    await test_session.rollback()
