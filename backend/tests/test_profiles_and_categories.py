import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image
from rest_framework import status

from apps.categories.models import Category, WorkerCategory
from apps.notifications.models import Notification
from tests.conftest import CategoryFactory


def make_test_image_file(name="avatar.png"):
    buf = io.BytesIO()
    img = Image.new("RGB", (50, 50), color="blue")
    img.save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


@pytest.mark.django_db
class TestProfilesAndCategories:
    def test_worker_cannot_self_verify_via_profile_patch(self, auth_client, unverified_worker):
        user, profile = unverified_worker
        client = auth_client(user)

        resp = client.patch(
            "/api/v1/profiles/worker/",
            {"is_verified": True, "verification_status": "VERIFIED", "bio": "Trying to self verify"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        profile.refresh_from_db()
        assert profile.is_verified is False
        assert profile.verification_status == "UNSUBMITTED"

    def test_worker_can_update_profile_upload_photo_and_portfolio(self, auth_client, unverified_worker):
        user, profile = unverified_worker
        client = auth_client(user)

        photo = make_test_image_file("worker.png")
        resp = client.patch(
            "/api/v1/profiles/worker/",
            {"bio": "Tajribali usta", "location": "Toshkent", "photo": photo},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.bio == "Tajribali usta"
        assert bool(profile.photo) is True

        p_resp = client.post(
            "/api/v1/profiles/worker/portfolio/",
            {"title": "Ofis ta'miri", "description": "200 kv.m ofis", "completed_year": 2025},
            format="json",
        )
        assert p_resp.status_code == status.HTTP_201_CREATED

    def test_admin_verifies_worker_and_ordinary_user_cannot(self, auth_client, unverified_worker, admin_user):
        w_user, w_profile = unverified_worker
        worker_client = auth_client(w_user)

        # Worker submits verification request
        req_resp = worker_client.post(
            "/api/v1/profiles/worker/verification-request/",
            {"notes": "Passport va sertifikat tayyor"},
            format="json",
        )
        assert req_resp.status_code == status.HTTP_200_OK
        assert req_resp.data["data"]["verification_status"] == "PENDING"

        # Worker cannot call admin verify endpoint
        forbidden = worker_client.post(
            f"/api/v1/admin/workers/{w_profile.id}/verify/",
            {"action": "APPROVE"},
            format="json",
        )
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN

        # Admin approves verification
        admin_client = auth_client(admin_user)
        ok_resp = admin_client.post(
            f"/api/v1/admin/workers/{w_profile.id}/verify/",
            {"action": "APPROVE", "notes": "Hujjatlar tasdiqlandi"},
            format="json",
        )
        assert ok_resp.status_code == status.HTTP_200_OK
        w_profile.refresh_from_db()
        assert w_profile.is_verified is True
        assert w_profile.verification_status == "VERIFIED"
        assert Notification.objects.filter(recipient=w_user, event_type="VERIFICATION_UPDATED").exists()

    def test_category_admin_permissions_and_max_10_limit(self, auth_client, verified_worker, admin_user):
        w_user, w_profile = verified_worker
        worker_client = auth_client(w_user)
        admin_client = auth_client(admin_user)

        # Worker cannot create category
        no_perm = worker_client.post(
            "/api/v1/categories/",
            {"slug": "illegal-cat", "name": "No Perm"},
            format="json",
        )
        assert no_perm.status_code == status.HTTP_403_FORBIDDEN

        # Admin creates 11 categories
        cats = [CategoryFactory(slug=f"cat-limit-{i}", name=f"Cat {i}") for i in range(11)]

        # Worker assigns 10 categories -> succeeds
        payload_10 = {
            "categories": [{"category_id": str(cats[i].id), "is_primary": (i == 0)} for i in range(10)]
        }
        r10 = worker_client.put("/api/v1/profiles/worker/categories/", payload_10, format="json")
        assert r10.status_code == status.HTTP_200_OK
        assert WorkerCategory.objects.filter(worker=w_profile).count() == 10

        # Worker attempts 11 categories -> rejected
        payload_11 = {
            "categories": [{"category_id": str(cats[i].id), "is_primary": (i == 0)} for i in range(11)]
        }
        r11 = worker_client.put("/api/v1/profiles/worker/categories/", payload_11, format="json")
        assert r11.status_code == status.HTTP_400_BAD_REQUEST

        # Direct ORM insert of 11th category must also be blocked by PostgreSQL trigger!
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkerCategory.objects.create(worker=w_profile, category=cats[10], is_primary=False)

        # Duplicate category assignment blocked
        dup_payload = {
            "categories": [
                {"category_id": str(cats[0].id), "is_primary": True},
                {"category_id": str(cats[0].id), "is_primary": False},
            ]
        }
        r_dup = worker_client.put("/api/v1/profiles/worker/categories/", dup_payload, format="json")
        assert r_dup.status_code == status.HTTP_400_BAD_REQUEST

        # Deactivating a category purges active worker assignments for it
        deact = admin_client.post(f"/api/v1/categories/{cats[0].id}/deactivate/")
        assert deact.status_code == status.HTTP_200_OK
        assert not WorkerCategory.objects.filter(worker=w_profile, category=cats[0]).exists()
        assert WorkerCategory.objects.filter(worker=w_profile).count() == 9
