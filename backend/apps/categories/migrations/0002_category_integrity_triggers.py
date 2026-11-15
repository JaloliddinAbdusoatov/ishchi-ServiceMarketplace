from django.db import migrations


TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION fn_enforce_worker_category_limit()
RETURNS TRIGGER AS $$
DECLARE
    v_cat_active BOOLEAN;
    v_count INT;
BEGIN
    -- Lock parent worker row to serialize concurrent assignments
    PERFORM 1 FROM profiles_worker WHERE id = NEW.worker_id FOR UPDATE;

    SELECT is_active INTO v_cat_active FROM categories_category WHERE id = NEW.category_id;
    IF v_cat_active IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'Cannot assign inactive category (%) to worker.', NEW.category_id
            USING ERRCODE = '23514';
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM categories_worker_category
    WHERE worker_id = NEW.worker_id AND id <> NEW.id;

    IF v_count >= 10 THEN
        RAISE EXCEPTION 'Worker (%) cannot have more than 10 assigned categories.', NEW.worker_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enforce_worker_category_limit ON categories_worker_category;
CREATE TRIGGER trg_enforce_worker_category_limit
BEFORE INSERT OR UPDATE ON categories_worker_category
FOR EACH ROW EXECUTE FUNCTION fn_enforce_worker_category_limit();

CREATE OR REPLACE FUNCTION fn_purge_deactivated_worker_categories()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_active = TRUE AND NEW.is_active = FALSE THEN
        DELETE FROM categories_worker_category WHERE category_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_purge_deactivated_worker_categories ON categories_category;
CREATE TRIGGER trg_purge_deactivated_worker_categories
AFTER UPDATE OF is_active ON categories_category
FOR EACH ROW EXECUTE FUNCTION fn_purge_deactivated_worker_categories();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_enforce_worker_category_limit ON categories_worker_category;
DROP FUNCTION IF EXISTS fn_enforce_worker_category_limit();
DROP TRIGGER IF EXISTS trg_purge_deactivated_worker_categories ON categories_category;
DROP FUNCTION IF EXISTS fn_purge_deactivated_worker_categories();
"""


SQLITE_TRIGGER_SQL = [
    """CREATE TRIGGER trg_enforce_worker_category_limit_insert
    BEFORE INSERT ON categories_worker_category BEGIN
      SELECT RAISE(ABORT, 'Cannot assign inactive category') WHERE NOT EXISTS
        (SELECT 1 FROM categories_category WHERE id = NEW.category_id AND is_active = 1);
      SELECT RAISE(ABORT, 'Worker cannot have more than 10 categories') WHERE
        (SELECT COUNT(*) FROM categories_worker_category WHERE worker_id = NEW.worker_id) >= 10;
    END""",
    """CREATE TRIGGER trg_enforce_worker_category_limit_update
    BEFORE UPDATE ON categories_worker_category BEGIN
      SELECT RAISE(ABORT, 'Cannot assign inactive category') WHERE NOT EXISTS
        (SELECT 1 FROM categories_category WHERE id = NEW.category_id AND is_active = 1);
      SELECT RAISE(ABORT, 'Worker cannot have more than 10 categories') WHERE
        (SELECT COUNT(*) FROM categories_worker_category WHERE worker_id = NEW.worker_id AND id <> NEW.id) >= 10;
    END""",
    """CREATE TRIGGER trg_purge_deactivated_worker_categories
    AFTER UPDATE OF is_active ON categories_category WHEN OLD.is_active = 1 AND NEW.is_active = 0
    BEGIN DELETE FROM categories_worker_category WHERE category_id = NEW.id; END""",
]


def install_triggers(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(TRIGGER_SQL)
    elif schema_editor.connection.vendor == "sqlite":
        for sql in SQLITE_TRIGGER_SQL:
            schema_editor.execute(sql)
    else:
        raise RuntimeError("Demo category integrity requires PostgreSQL or SQLite.")


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE_SQL)
    elif schema_editor.connection.vendor == "sqlite":
        for name in ("trg_enforce_worker_category_limit_insert", "trg_enforce_worker_category_limit_update", "trg_purge_deactivated_worker_categories"):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}")


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(install_triggers, remove_triggers),
    ]
