from .base import *

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mysite",
        "USER": "christine",
        "PASSWORD": "admin",
        "HOST": "localhost",
        "PORT": "",
    }
}