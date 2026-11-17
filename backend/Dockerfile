FROM python:3.14-slim-bookworm@sha256:3fe1a0b6c2d6b2ebb572906cdabeca75aeb558c0c17db5ffefbcf8094871c32b
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production ISHCHI_ENV=production
WORKDIR /app
COPY requirements-production.lock ./
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements-production.lock \
    && groupadd --gid 10001 ishchi && useradd --uid 10001 --gid 10001 --no-create-home ishchi \
    && mkdir -p /app/media /app/staticfiles && chown -R 10001:10001 /app
COPY --chown=10001:10001 manage.py ./
COPY --chown=10001:10001 apps ./apps
COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 static ./static
COPY --chown=10001:10001 templates ./templates
USER 10001:10001
# This setting uses a dummy DB and refuses production mode. No build-time secrets.
RUN ISHCHI_ENV=build DJANGO_SETTINGS_MODULE=config.settings.build python manage.py collectstatic --noinput
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-m", "config.container_health"]
CMD ["gunicorn", "--config", "config/gunicorn.py", "config.wsgi:application"]
