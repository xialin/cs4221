"""
WSGI config for cs4221 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os, sys
sys.path.append('/Applications/djangostack-1.10.6-0/apps/django/django_projects/cs4221')
os.environ.setdefault("PYTHON_EGG_CACHE", "/Applications/djangostack-1.10.6-0/apps/django/django_projects/cs4221/egg_cache")


from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cs4221.settings")

application = get_wsgi_application()
