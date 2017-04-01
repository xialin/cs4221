from django.conf.urls import url

from hello.views import HomePageView
from hello import views

urlpatterns = [
    url(r'^$', HomePageView.as_view(), name='home'),
    url(r'^upload$', views.upload, name='upload'),
    url(r'^generate$', views.generate, name='generate'),
    url(r'^choose_key$', views.choose_key, name='choose_key'),
    url(r'^selected_key$', views.selected_key, name='selected_key'),
]
