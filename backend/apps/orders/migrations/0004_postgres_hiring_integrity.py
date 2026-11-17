"""Proposed current-MVP constraints. PostgreSQL execution requires separate approval."""
from django.db import migrations


TABLES = {
    "orders_service_order": "id",
    "orders_service_order_assigned_workers": "serviceorder_id",
    "applications_order_application": "order_id",
    "invitations_order_invitation": "order_id",
}

SQL = """
CREATE FUNCTION ishchi_check_hiring(p_order uuid) RETURNS void AS $$
DECLARE job orders_service_order%ROWTYPE;
BEGIN
    SELECT * INTO job FROM orders_service_order WHERE id = p_order FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    IF (SELECT COUNT(*) FROM (
        SELECT workerprofile_id FROM orders_service_order_assigned_workers WHERE serviceorder_id = p_order
        UNION SELECT job.assigned_worker_id WHERE job.assigned_worker_id IS NOT NULL
    ) hired) > job.capacity THEN
        RAISE EXCEPTION 'Order capacity exceeded' USING ERRCODE = '23514';
    END IF;
    IF job.assigned_worker_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM orders_service_order_assigned_workers
        WHERE serviceorder_id = p_order AND workerprofile_id = job.assigned_worker_id
    ) THEN
        RAISE EXCEPTION 'Primary worker must belong to hired team' USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM applications_order_application a WHERE a.order_id = p_order AND a.status = 'ACCEPTED'
        AND NOT EXISTS (SELECT 1 FROM orders_service_order_assigned_workers h
            WHERE h.serviceorder_id = p_order AND h.workerprofile_id = a.worker_id)
    ) OR EXISTS (
        SELECT 1 FROM invitations_order_invitation i WHERE i.order_id = p_order AND i.status = 'ACCEPTED'
        AND NOT EXISTS (SELECT 1 FROM orders_service_order_assigned_workers h
            WHERE h.serviceorder_id = p_order AND h.workerprofile_id = i.worker_id)
    ) OR EXISTS (
        SELECT 1 FROM orders_service_order_assigned_workers h WHERE h.serviceorder_id = p_order
        AND NOT EXISTS (SELECT 1 FROM applications_order_application a
            WHERE a.order_id = p_order AND a.worker_id = h.workerprofile_id AND a.status = 'ACCEPTED')
        AND NOT EXISTS (SELECT 1 FROM invitations_order_invitation i
            WHERE i.order_id = p_order AND i.worker_id = h.workerprofile_id AND i.status = 'ACCEPTED')
    ) THEN
        RAISE EXCEPTION 'Accepted request and hired team are inconsistent' USING ERRCODE = '23514';
    END IF;
    IF EXISTS (SELECT 1 FROM invitations_order_invitation WHERE order_id = p_order AND employer_id <> job.employer_id) THEN
        RAISE EXCEPTION 'Invitation owner must match order owner' USING ERRCODE = '23514';
    END IF;
END;
$$ LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp;

CREATE FUNCTION ishchi_hiring_integrity_event() RETURNS trigger AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        PERFORM ishchi_check_hiring((to_jsonb(OLD)->>TG_ARGV[0])::uuid);
    END IF;
    IF TG_OP <> 'DELETE' THEN
        PERFORM ishchi_check_hiring((to_jsonb(NEW)->>TG_ARGV[0])::uuid);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp;
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    # Reconcile trigger tables/columns with the historical models, offline too.
    assert apps.get_model("orders", "ServiceOrder")._meta.db_table == "orders_service_order"
    assert apps.get_model("orders", "ServiceOrder")._meta.get_field("assigned_workers").remote_field.through._meta.db_table == "orders_service_order_assigned_workers"
    schema_editor.execute(SQL, params=None)
    for table, column in TABLES.items():
        schema_editor.execute(f"""CREATE CONSTRAINT TRIGGER ishchi_hiring_integrity
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION ishchi_hiring_integrity_event('{column}')""")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS ishchi_hiring_integrity ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS ishchi_hiring_integrity_event(); DROP FUNCTION IF EXISTS ishchi_check_hiring(uuid);")


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_payment_display_label"),
        ("applications", "0002_remove_orderapplication_uq_single_accepted_application_per_order"),
        ("invitations", "0002_remove_orderinvitation_uq_single_accepted_invitation_per_order"),
    ]
    operations = [migrations.RunPython(install, uninstall)]
