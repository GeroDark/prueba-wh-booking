"""Database guarantee against double bookings (PostgreSQL only, see D02 and D07).

Two bookings of the same property cannot share a night while both are PENDING or CONFIRMED.
The stay is the half-open range [check_in, check_out), so a check-out and a check-in on the
same day do not collide. btree_gist lets GiST combine the "=" on property_id with the range "&&".

The constraint lives in a migration instead of Meta.constraints because SQLite has no exclusion
constraints; on SQLite the migration does nothing and the service layer protects the data.
"""

from django.db import migrations

CONSTRAINT = "bookings_booking_no_overlapping_stays"


def add_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    schema_editor.execute(
        f"""
        ALTER TABLE bookings_booking ADD CONSTRAINT {CONSTRAINT}
        EXCLUDE USING gist (
            property_id WITH =,
            daterange(check_in, check_out, '[)') WITH &&
        )
        WHERE (status IN ('pending', 'confirmed'))
        """
    )


def remove_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"ALTER TABLE bookings_booking DROP CONSTRAINT IF EXISTS {CONSTRAINT}")


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0002_booking_total_and_lines"),
    ]

    operations = [
        migrations.RunPython(add_constraint, remove_constraint),
    ]
