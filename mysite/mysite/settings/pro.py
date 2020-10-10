from .base import *

DEBUG = False
ADMINS = (("Christine Nyries Yambao", "yambao.cn@gmail.com"),)
ALLOWED_HOSTS = ["mysiteproject.com", "www.mysiteproject.com"]
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
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
