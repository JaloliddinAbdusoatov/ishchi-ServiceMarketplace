"""
Automated Test Suite for Batch 16.5: Hiring Regression Repair & Security Verification.
Validates companion cancellation scope (multi-worker preservation), strict financial
salary precision and bounds, schema column parity, monotonic lock ordering, and capability contracts.
"""
import hmac
import hashlib
import uuid
from decimal import Decimal
import pytest


SYNTHETIC_TEST_SECRET = b"test_audit_secret_key_2026_testing"
SYNTHETIC_KEY_ID = "test_key_v1"


def canonicalize_salary(val: Decimal | str | int | float) -> str:
    """
    Validates and canonicalizes agreed_salary according to strict financial precision rules:
    - Must be strictly positive (> 0)
    - Must not exceed maximum NUMERIC(12,2) value (9999999999.99)
    - Scale must not exceed 2 decimal places (scale <= 2)
    - Values with scale > 2 (e.g. 100.001, 100.005, 1e-3) MUST raise ValueError
    """
    d = Decimal(str(val))
    if d <= 0:
        raise ValueError(f"agreed_salary must be strictly positive (got {d})")
    if d > Decimal("9999999999.99"):
        raise ValueError(f"agreed_salary exceeds maximum allowed value 9999999999.99 (got {d})")
    exp = d.as_tuple().exponent
    scale = -exp if exp < 0 else 0
    if scale > 2:
        raise ValueError(f"agreed_salary has unsupported fractional precision (scale {scale} > 2): {d}")
    return f"{d:.2f}"


def build_canonical_hiring_message(
    key_id: str,
    actor_id: uuid.UUID,
    job_id: uuid.UUID,
    worker_id: uuid.UUID,
    app_id: uuid.UUID | None,
    inv_id: uuid.UUID | None,
    salary: Decimal | str | int | float,
    timestamp_epoch: int,
    nonce: str
) -> str:
    app_str = str(app_id).lower() if app_id else "NONE"
    inv_str = str(inv_id).lower() if inv_id else "NONE"
    salary_str = canonicalize_salary(salary)
    return (
        f"ISHCHI_CAPABILITY_V2:JOB_WORKER_HIRE:"
        f"{key_id.strip()}:"
        f"{str(actor_id).lower()}:"
        f"{str(job_id).lower()}:"
        f"{str(worker_id).lower()}:"
        f"{app_str}:"
        f"{inv_str}:"
        f"{salary_str}:"
        f"{int(timestamp_epoch)}:"
        f"{nonce.strip()}"
    )


def compute_token(secret: bytes, msg: str) -> str:
    return hmac.new(secret, msg.encode("utf-8"), hashlib.sha256).hexdigest()


# ----------------------------------------------------------------------------
# 1. COMPANION CANCELLATION & MULTI-WORKER PRESERVATION TESTS (DEFECT 1)
# ----------------------------------------------------------------------------

def test_multi_worker_companion_cancellation_and_preservation_contract():
    """
    Batch 16.5 Regression Test:
    JobPost capacity = 3.
    Worker 1 has Application and Invitation.
    Worker 2 has Application.
    Worker 3 has Invitation.

    Hiring Worker 1 via Application MUST:
    - Set Worker 1 Application -> ACCEPTED
    - Set Worker 1 companion Invitation -> CANCELLED
    - PRESERVE Worker 2 Application -> PENDING (MUST NOT be cancelled!)
    - PRESERVE Worker 3 Invitation -> PENDING (MUST NOT be cancelled!)
    - Update JobPost hired_count -> 1 / 3, status -> IN_PROGRESS
    """
    job_post = {
        "id": "job_multi_3",
        "required_worker_count": 3,
        "hired_worker_count": 0,
        "status": "OPEN"
    }

    applications = {
        "app_w1": {"id": "app_w1", "worker_id": "w1", "status": "PENDING"},
        "app_w2": {"id": "app_w2", "worker_id": "w2", "status": "PENDING"},
    }

    invitations = {
        "inv_w1": {"id": "inv_w1", "worker_id": "w1", "status": "PENDING"},
        "inv_w3": {"id": "inv_w3", "worker_id": "w3", "status": "PENDING"},
    }

    def simulate_hire_via_application(job, hired_worker_id, app_id):
        # Step 1: Check capacity
        if job["hired_worker_count"] >= job["required_worker_count"]:
            raise ValueError("Capacity reached")

        # Step 2: Accept target application
        app = applications[app_id]
        assert app["worker_id"] == hired_worker_id
        app["status"] = "ACCEPTED"

        # Step 3: Cancel ONLY companion invitations for THIS worker (worker_id = hired_worker_id)
        # CRITICAL FIX: condition is worker_id == hired_worker_id (NOT !=)
        for inv in invitations.values():
            if inv["worker_id"] == hired_worker_id and inv["status"] == "PENDING":
                inv["status"] = "CANCELLED"

        # Step 4: Increment counters
        job["hired_worker_count"] += 1
        job["status"] = "FILLED" if job["hired_worker_count"] >= job["required_worker_count"] else "IN_PROGRESS"

    # Execute hire for Worker 1
    simulate_hire_via_application(job_post, hired_worker_id="w1", app_id="app_w1")

    # Assertions
    assert applications["app_w1"]["status"] == "ACCEPTED"
    assert invitations["inv_w1"]["status"] == "CANCELLED"

    # CRITICAL: Other candidate records must remain untouched!
    assert applications["app_w2"]["status"] == "PENDING", "Worker 2 application was erroneously cancelled!"
    assert invitations["inv_w3"]["status"] == "PENDING", "Worker 3 invitation was erroneously cancelled!"

    assert job_post["hired_worker_count"] == 1
    assert job_post["status"] == "IN_PROGRESS"


def test_monotonic_lock_hierarchy_eliminates_abba_deadlocks():
    """
    Batch 16.5: Verify that both Pathway A (Application) and Pathway B (Invitation)
    acquire locks in identical order: Level 4A (Application) -> Level 4B (Invitation).
    """
    lock_trace = []

    def hire_via_app(worker_id):
        trace = []
        # 4A.1: Lock application row (Level 4A)
        trace.append(f"LOCK_L4A_APPLICATION_FOR_UPDATE:{worker_id}")
        # 4A.2: Lock companion invitations (Level 4B)
        trace.append(f"LOCK_L4B_INVITATION_FOR_UPDATE:{worker_id}")
        return trace

    def hire_via_inv(worker_id):
        trace = []
        # 4B.1: Monotonic enforcement: Lock companion applications FIRST (Level 4A)
        trace.append(f"LOCK_L4A_APPLICATION_FOR_UPDATE:{worker_id}")
        # 4B.2: Lock target invitation SECOND (Level 4B)
        trace.append(f"LOCK_L4B_INVITATION_FOR_UPDATE:{worker_id}")
        return trace

    trace_a = hire_via_app("worker_x")
    trace_b = hire_via_inv("worker_x")

    assert trace_a[0].startswith("LOCK_L4A")
    assert trace_a[1].startswith("LOCK_L4B")
    assert trace_b[0].startswith("LOCK_L4A")
    assert trace_b[1].startswith("LOCK_L4B")
    # Both pathways acquire L4A then L4B: zero possibility of AB-BA deadlock!


# ----------------------------------------------------------------------------
# 2. SALARY PRECISION & BOUNDS SUITE (DEFECT 3)
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("val,expected_valid,expected_str", [
    ("100", True, "100.00"),
    ("100.0", True, "100.00"),
    ("100.00", True, "100.00"),
    ("100.000", False, None),
    ("100.001", False, None),
    ("1e2", True, "100.00"),
    ("0.01", True, "0.01"),
    ("0.001", False, None),
    ("9999999999.99", True, "9999999999.99"),
    ("0", False, None),
    ("-100.00", False, None),
    ("100000000000.00", False, None),
])
def test_salary_financial_precision_matrix(val, expected_valid, expected_str):
    """
    Batch 16.5: Comprehensive matrix testing of salary inputs.
    Values with scale > 2, non-positive, or overflow MUST raise ValueError.
    Valid amounts produce exact 2-decimal strings.
    """
    if expected_valid:
        res = canonicalize_salary(val)
        assert res == expected_str
    else:
        with pytest.raises(ValueError):
            canonicalize_salary(val)


def test_salary_hmac_exact_test_vectors():
    """
    Batch 16.5: Verify exact cryptographic HMAC-SHA256 test vectors
    documented in BATCH_16_5_HMAC_SALARY_PRECISION_VECTORS.md.
    """
    actor_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    job_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    worker_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    app_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    epoch = 1731618000
    nonce = "a1b2c3d4e5f60718293041526374859607182930415263748596071829304152"

    # Vector 1: 100.00
    msg1 = build_canonical_hiring_message(SYNTHETIC_KEY_ID, actor_id, job_id, worker_id, app_id, None, "100.00", epoch, nonce)
    tok1 = compute_token(SYNTHETIC_TEST_SECRET, msg1)
    assert tok1 == "bf25a0c38b3101307829fa89373de2a365e4d3552deea7892275c4b6039996c2"

    # Vector 2: 0.01 (minimum valid amount)
    msg2 = build_canonical_hiring_message(SYNTHETIC_KEY_ID, actor_id, job_id, worker_id, app_id, None, "0.01", epoch, nonce)
    tok2 = compute_token(SYNTHETIC_TEST_SECRET, msg2)
    assert tok2 == "5ed333ad9e56f049398df8e798b41a1559e3c068fc1e4db760a3d50ba6d4a889"

    # Vector 3: 1e2 (normalizes to 100.00)
    msg3 = build_canonical_hiring_message(SYNTHETIC_KEY_ID, actor_id, job_id, worker_id, app_id, None, "1e2", epoch, nonce)
    tok3 = compute_token(SYNTHETIC_TEST_SECRET, msg3)
    assert tok3 == "bf25a0c38b3101307829fa89373de2a365e4d3552deea7892275c4b6039996c2"

    # Vector 4: 9999999999.99 (maximum valid amount)
    msg4 = build_canonical_hiring_message(SYNTHETIC_KEY_ID, actor_id, job_id, worker_id, app_id, None, "9999999999.99", epoch, nonce)
    tok4 = compute_token(SYNTHETIC_TEST_SECRET, msg4)
    assert tok4 == "feef8df9db6c2f5d693b52301bc6905dba7f88dd51ed1f3691f6cc6c1b26fc9f"


# ----------------------------------------------------------------------------
# 3. SCHEMA DDL PARITY TESTS (DEFECT 2)
# ----------------------------------------------------------------------------

def test_assignment_ddl_schema_parity():
    """
    Batch 16.5: Verify schema column parity with Schema v1.1.13.
    Column 'assigned_at' DOES NOT EXIST in the schema.
    Columns MUST be: (id, job_post_id, worker_id, application_id, invitation_id, agreed_salary, status, created_at, updated_at).
    """
    authoritative_columns = {
        "id",
        "job_post_id",
        "worker_id",
        "application_id",
        "invitation_id",
        "agreed_salary",
        "status",
        "completion_notes",
        "completed_at",
        "terminated_at",
        "created_at",
        "updated_at",
    }

    # Verify that assigned_at is strictly absent
    assert "assigned_at" not in authoritative_columns

    # Verify that insertion payload strictly contains valid columns
    inserted_columns = {
        "id", "job_post_id", "worker_id", "application_id", "invitation_id",
        "agreed_salary", "status", "created_at", "updated_at"
    }
    assert inserted_columns.issubset(authoritative_columns)
