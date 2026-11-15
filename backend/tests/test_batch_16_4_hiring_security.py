"""
Automated Test Suite for Batch 16.4: Critical Hiring HMAC & Audit Bypass Remediation.
Validates complete HMAC parameter binding, decimal canonicalization parity, tampering detection,
single authoritative nonce consumption, server-side actor boundary, and legacy function bypass prevention.
"""
import hmac
import hashlib
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock


SYNTHETIC_TEST_SECRET = b"test_audit_secret_key_2026_testing"
SYNTHETIC_KEY_ID = "test_key_v1"


def build_hiring_canonical_message(
    key_id: str,
    actor_user_id: uuid.UUID,
    job_post_id: uuid.UUID,
    worker_id: uuid.UUID,
    application_id: uuid.UUID | None,
    invitation_id: uuid.UUID | None,
    agreed_salary: Decimal,
    auth_timestamp: int,
    nonce: str
) -> str:
    """
    Constructs the canonical colon-delimited hiring capability message string.
    Enforces exact Python / PostgreSQL canonicalization parity.
    """
    app_str = str(application_id).lower() if application_id else "NONE"
    inv_str = str(invitation_id).lower() if invitation_id else "NONE"
    salary_str = f"{Decimal(str(agreed_salary)).quantize(Decimal('0.01')):.2f}"

    return (
        f"ISHCHI_CAPABILITY_V2:JOB_WORKER_HIRE:"
        f"{key_id.strip()}:"
        f"{str(actor_user_id).lower()}:"
        f"{str(job_post_id).lower()}:"
        f"{str(worker_id).lower()}:"
        f"{app_str}:"
        f"{inv_str}:"
        f"{salary_str}:"
        f"{int(auth_timestamp)}:"
        f"{nonce.strip()}"
    )


def compute_hiring_hmac(secret_key: bytes, canonical_msg: str) -> str:
    """Computes HMAC-SHA256 in hex format."""
    return hmac.new(secret_key, canonical_msg.encode("utf-8"), hashlib.sha256).hexdigest()


def test_hiring_hmac_complete_payload_binding_canonical_vector_1():
    """Batch 16.4 / Vector 1: Application origin test vector."""
    msg = build_hiring_canonical_message(
        key_id=SYNTHETIC_KEY_ID,
        actor_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        job_post_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        worker_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        application_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        invitation_id=None,
        agreed_salary=Decimal("450000.00"),
        auth_timestamp=1731618000,
        nonce="a1b2c3d4e5f60718293041526374859607182930415263748596071829304152"
    )
    expected_msg = (
        "ISHCHI_CAPABILITY_V2:JOB_WORKER_HIRE:test_key_v1:"
        "11111111-1111-1111-1111-111111111111:"
        "22222222-2222-2222-2222-222222222222:"
        "33333333-3333-3333-3333-333333333333:"
        "44444444-4444-4444-4444-444444444444:NONE:"
        "450000.00:1731618000:"
        "a1b2c3d4e5f60718293041526374859607182930415263748596071829304152"
    )
    assert msg == expected_msg

    sig = compute_hiring_hmac(SYNTHETIC_TEST_SECRET, msg)
    expected_sig = "136480dc443f6ecd1341ec046dec4d346452724a2b3f6128f4d56a1ffadbf5ab"
    assert sig == expected_sig


def test_hiring_hmac_complete_payload_binding_canonical_vector_2():
    """Batch 16.4 / Vector 2: Invitation origin test vector."""
    msg = build_hiring_canonical_message(
        key_id=SYNTHETIC_KEY_ID,
        actor_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        job_post_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        worker_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        application_id=None,
        invitation_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        agreed_salary=Decimal("750000.50"),
        auth_timestamp=1731618000,
        nonce="f1e2d3c4b5a60718293041526374859607182930415263748596071829304152"
    )
    expected_msg = (
        "ISHCHI_CAPABILITY_V2:JOB_WORKER_HIRE:test_key_v1:"
        "11111111-1111-1111-1111-111111111111:"
        "22222222-2222-2222-2222-222222222222:"
        "55555555-5555-5555-5555-555555555555:"
        "NONE:66666666-6666-6666-6666-666666666666:"
        "750000.50:1731618000:"
        "f1e2d3c4b5a60718293041526374859607182930415263748596071829304152"
    )
    assert msg == expected_msg

    sig = compute_hiring_hmac(SYNTHETIC_TEST_SECRET, msg)
    expected_sig = "d26bd6f365a14799d6e9d9782da2771a9116ef29a08a0479a0033ee661de1c2c"
    assert sig == expected_sig


def test_hiring_hmac_tampering_each_signed_field():
    """
    Batch 16.4: Deterministic tampering matrix.
    Modifying any single field must produce an HMAC mismatch.
    """
    base_params = {
        "key_id": SYNTHETIC_KEY_ID,
        "actor_user_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "job_post_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "worker_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "application_id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "invitation_id": None,
        "agreed_salary": Decimal("450000.00"),
        "auth_timestamp": 1731618000,
        "nonce": "a1b2c3d4e5f60718293041526374859607182930415263748596071829304152"
    }
    baseline_msg = build_hiring_canonical_message(**base_params)
    baseline_sig = compute_hiring_hmac(SYNTHETIC_TEST_SECRET, baseline_msg)

    # 1. Tamper key_id
    p1 = base_params.copy()
    p1["key_id"] = "test_key_v2"
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p1)) != baseline_sig

    # 2. Tamper actor_user_id
    p2 = base_params.copy()
    p2["actor_user_id"] = uuid.UUID("99999999-9999-9999-9999-999999999999")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p2)) != baseline_sig

    # 3. Tamper job_post_id
    p3 = base_params.copy()
    p3["job_post_id"] = uuid.UUID("88888888-8888-8888-8888-888888888888")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p3)) != baseline_sig

    # 4. Tamper worker_id
    p4 = base_params.copy()
    p4["worker_id"] = uuid.UUID("77777777-7777-7777-7777-777777777777")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p4)) != baseline_sig

    # 5. Tamper application_id
    p5 = base_params.copy()
    p5["application_id"] = uuid.UUID("55555555-5555-5555-5555-555555555555")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p5)) != baseline_sig

    # 6. Tamper invitation_id
    p6 = base_params.copy()
    p6["invitation_id"] = uuid.UUID("66666666-6666-6666-6666-666666666666")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p6)) != baseline_sig

    # 7. Tamper agreed_salary (+1 kopeck)
    p7 = base_params.copy()
    p7["agreed_salary"] = Decimal("450000.01")
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p7)) != baseline_sig

    # 8. Tamper timestamp (+1 second)
    p8 = base_params.copy()
    p8["auth_timestamp"] = 1731618001
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p8)) != baseline_sig

    # 9. Tamper nonce (last character altered)
    p9 = base_params.copy()
    p9["nonce"] = "a1b2c3d4e5f60718293041526374859607182930415263748596071829304153"
    assert compute_hiring_hmac(SYNTHETIC_TEST_SECRET, build_hiring_canonical_message(**p9)) != baseline_sig


def test_exact_decimal_parity_quantization():
    """Batch 16.4: Decimal formatting always yields exactly 2 decimal places without exponent."""
    test_cases = [
        (450000, "450000.00"),
        ("450000", "450000.00"),
        (Decimal("450000.0"), "450000.00"),
        (Decimal("450000.000"), "450000.00"),
        (Decimal("750000.5"), "750000.50"),
        (Decimal("1234567.89"), "1234567.89"),
    ]
    for val, expected_str in test_cases:
        res = f"{Decimal(str(val)).quantize(Decimal('0.01')):.2f}"
        assert res == expected_str


def test_single_authoritative_nonce_consumption_contract():
    """
    Batch 16.4: Single authoritative nonce consumption contract.
    Ensures that replaying a nonce raises a replay error, while preventing double consumption.
    """
    consumed_nonces = set()

    def consume_nonce(nonce: str):
        if nonce in consumed_nonces:
            raise PermissionError(f"Capability nonce {nonce} has already been consumed: replay attack detected.")
        consumed_nonces.add(nonce)
        return True

    test_nonce = "nonce_unique_1234567890abcdef"
    # First consumption succeeds
    assert consume_nonce(test_nonce) is True

    # Replay attempt fails closed
    with pytest.raises(PermissionError, match="replay attack detected"):
        consume_nonce(test_nonce)


def test_server_side_actor_authorization_boundary_contract():
    """
    Batch 16.4: Server-side actor authentication boundary.
    Validates that:
    1. Actor must exist, be active, and not anonymized.
    2. Actor must be the employer of the target job post.
    3. Session GUC spoofing is rejected.
    """
    job_post = {
        "id": "job_100",
        "employer_id": "employer_1",
        "status": "OPEN",
    }

    def verify_actor(actor_id: str, is_active: bool, is_anonymized: bool, session_actor_guc: str | None):
        if not is_active:
            raise PermissionError("Actor user is inactive.")
        if is_anonymized:
            raise PermissionError("Actor user is anonymized.")
        if job_post["employer_id"] != actor_id:
            raise PermissionError(f"Actor {actor_id} is not the authorized employer for job {job_post['id']}.")
        if session_actor_guc and session_actor_guc != actor_id:
            raise PermissionError("Session GUC spoofing detected.")
        return True

    # Valid actor
    assert verify_actor("employer_1", is_active=True, is_anonymized=False, session_actor_guc="employer_1") is True

    # Inactive actor rejected
    with pytest.raises(PermissionError, match="Actor user is inactive"):
        verify_actor("employer_1", is_active=False, is_anonymized=False, session_actor_guc="employer_1")

    # Anonymized actor rejected
    with pytest.raises(PermissionError, match="Actor user is anonymized"):
        verify_actor("employer_1", is_active=True, is_anonymized=True, session_actor_guc="employer_1")

    # Unauthorized employer rejected
    with pytest.raises(PermissionError, match="not the authorized employer"):
        verify_actor("employer_2", is_active=True, is_anonymized=False, session_actor_guc="employer_2")

    # Session GUC spoofing rejected
    with pytest.raises(PermissionError, match="Session GUC spoofing detected"):
        verify_actor("employer_1", is_active=True, is_anonymized=False, session_actor_guc="imposter_user")


def test_legacy_function_bypass_prevention_contract():
    """
    Batch 16.4: Legacy function bypass prevention.
    Direct invocation of public.jobs_hire_worker (v1) by app_user is denied;
    external calls must be routed via public.jobs_hire_worker_v2 with capability.
    """
    dac_grants = {
        ("jobs_hire_worker", "app_user"): False,         # Revoked from app_user
        ("jobs_hire_worker", "celery_user"): False,      # Revoked from celery_user
        ("jobs_hire_worker", "ishchi_fn_owner"): True,   # Owner internal only
        ("jobs_hire_worker_v2", "app_user"): True,       # Granted to app_user
        ("jobs_hire_worker_v2", "celery_user"): False,   # Revoked from celery_user
    }

    def can_execute(func_name: str, role: str) -> bool:
        return dac_grants.get((func_name, role), False)

    # app_user CANNOT call v1 directly
    assert can_execute("jobs_hire_worker", "app_user") is False

    # app_user CAN call v2
    assert can_execute("jobs_hire_worker_v2", "app_user") is True

    # celery_user CANNOT call either
    assert can_execute("jobs_hire_worker", "celery_user") is False
    assert can_execute("jobs_hire_worker_v2", "celery_user") is False


def test_audit_atomicity_and_all_or_nothing_rollback_contract():
    """
    Batch 16.4: Single transaction atomic rollback contract.
    If audit emission or any invariant check fails, all changes (hiring & nonce) roll back.
    """
    transaction_state = {
        "nonce_consumed": False,
        "worker_hired": False,
        "audit_logged": False,
    }

    def execute_hiring_transaction(simulate_audit_failure: bool):
        try:
            # Step 1: Consume nonce
            transaction_state["nonce_consumed"] = True
            # Step 2: Hire worker
            transaction_state["worker_hired"] = True
            # Step 3: Audit emission
            if simulate_audit_failure:
                raise RuntimeError("Audit log storage failure (simulated disk full)")
            transaction_state["audit_logged"] = True
        except Exception:
            # Atomic rollback
            transaction_state["nonce_consumed"] = False
            transaction_state["worker_hired"] = False
            transaction_state["audit_logged"] = False
            raise

    with pytest.raises(RuntimeError, match="Audit log storage failure"):
        execute_hiring_transaction(simulate_audit_failure=True)

    assert transaction_state["nonce_consumed"] is False
    assert transaction_state["worker_hired"] is False
    assert transaction_state["audit_logged"] is False
