import os
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

UZ_PHONE_REGEX = re.compile(r"^\+998[0-9]{9}$")

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".doc", ".docx", ".txt"}


def validate_uz_phone(value: str) -> str:
    if not value or not UZ_PHONE_REGEX.match(value):
        raise ValidationError("Phone number must match Uzbekistan format +998XXXXXXXXX.")
    return value


def validate_image_file(file_obj):
    if not file_obj:
        return
    max_bytes = getattr(settings, "MAX_UPLOAD_IMAGE_SIZE_MB", 5) * 1024 * 1024
    if file_obj.size > max_bytes:
        raise ValidationError(f"Image size must not exceed {getattr(settings, 'MAX_UPLOAD_IMAGE_SIZE_MB', 5)} MB.")

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported image extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}.")

    try:
        pos = file_obj.tell()
        img = Image.open(file_obj)
        img.verify()
        file_obj.seek(pos)
    except (UnidentifiedImageError, Exception) as exc:
        raise ValidationError("Uploaded file is not a valid image.") from exc


def validate_chat_attachment(file_obj):
    if not file_obj:
        return
    max_bytes = getattr(settings, "MAX_UPLOAD_ATTACHMENT_SIZE_MB", 5) * 1024 * 1024
    if file_obj.size > max_bytes:
        raise ValidationError(
            f"Attachment size must not exceed {getattr(settings, 'MAX_UPLOAD_ATTACHMENT_SIZE_MB', 5)} MB."
        )

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ValidationError(
            f"Unsupported attachment type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))}."
        )

    if ext in ALLOWED_IMAGE_EXTENSIONS:
        validate_image_file(file_obj)
