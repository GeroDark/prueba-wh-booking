"""Migrations run by themselves on every deploy, so the ones that can lose data must be reviewed.

A migration with any operation below fails this test (and CI) unless its class declares
`reviewed_data_safety = "<why it is safe>"`. The sentence shows up in the pull request, so a
column or table is never dropped in production without someone reading why (D38).
"""

import pytest
from django.db.migrations import operations
from django.db.migrations.loader import MigrationLoader

RISKY_OPERATIONS = (
    operations.RemoveField,  # drops a column and its data
    operations.DeleteModel,  # drops a table
    operations.RunSQL,  # arbitrary SQL
    operations.RunPython,  # arbitrary code, may update or delete rows
)


def project_migrations():
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return [
        migration
        for migration in loader.disk_migrations.values()
        if migration.__module__.startswith("apps.")
    ]


def risky_operations(migration):
    return [type(op).__name__ for op in migration.operations if isinstance(op, RISKY_OPERATIONS)]


def test_there_are_project_migrations_to_check():
    assert len(project_migrations()) > 10


@pytest.mark.parametrize("migration", project_migrations(), ids=lambda m: f"{m.app_label}.{m.name}")
def test_migrations_that_can_lose_data_are_reviewed(migration):
    risky = risky_operations(migration)
    reason = getattr(migration, "reviewed_data_safety", "").strip()

    assert not risky or reason, (
        f"{migration.app_label}.{migration.name} uses {', '.join(risky)}, which can lose data in "
        "production. Check it, then add to the Migration class: "
        'reviewed_data_safety = "<why it is safe>".'
    )


def test_the_check_catches_a_column_drop():
    from django.db import migrations

    class Migration(migrations.Migration):
        operations = [migrations.RemoveField(model_name="booking", name="total")]

    assert risky_operations(Migration("0099_drop", "bookings")) == ["RemoveField"]
