import os
import re
import zipfile
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
    if any(char in file_obj.name for char in ("/", "\\", "\x00", "\r", "\n")):
        raise ValidationError("Invalid attachment filename.")
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
    else:
        pos = file_obj.tell()
        try:
            file_obj.seek(0)
            header = file_obj.read(8)
            file_obj.seek(0)
            if ext == ".pdf" and not header.startswith(b"%PDF-"):
                raise ValidationError("Attachment content does not match PDF type.")
            if ext == ".doc" and header != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
                raise ValidationError("Attachment content does not match DOC type.")
            if ext == ".docx":
                try:
                    with zipfile.ZipFile(file_obj) as archive:
                        entries = archive.infolist()
                        names = {entry.filename for entry in entries}
                        if not {"[Content_Types].xml", "word/document.xml"} <= names or any(
                            name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/")
                            or name.lower().endswith("vbaproject.bin") for name in names
                        ) or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024:
                            raise ValidationError("Invalid DOCX attachment.")
                except (zipfile.BadZipFile, OSError) as exc:
                    raise ValidationError("Invalid DOCX attachment.") from exc
            if ext == ".txt":
                raw = file_obj.read()
                try:
                    raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValidationError("Text attachments must use UTF-8.") from exc
                if not raw or b"\x00" in raw:
                    raise ValidationError("Invalid text attachment.")
        finally:
            file_obj.seek(pos)
    expected_mime = {
        ".pdf": {"application/pdf"}, ".doc": {"application/msword"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ".txt": {"text/plain"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"},
        ".png": {"image/png"}, ".webp": {"image/webp"},
    }
    declared = getattr(file_obj, "content_type", None)
    if declared and declared.split(";", 1)[0].strip().lower() not in expected_mime[ext] | {"application/octet-stream"}:
        raise ValidationError("Attachment MIME type does not match its extension.")
