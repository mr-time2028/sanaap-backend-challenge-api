"""Django project package — expose the Celery app on package import."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
