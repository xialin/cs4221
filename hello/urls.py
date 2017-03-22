from django.conf.urls import url

from hello.views import HomePageView
from hello import views

urlpatterns = [
    url(r'^$', HomePageView.as_view(), name='home'),
     url(r'^upload$', views.upload, name='upload'),

]
