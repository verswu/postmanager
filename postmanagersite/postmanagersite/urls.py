from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views

from postmanager import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': 'home'}, name='logout'),
    url(r'^manage/$', views.manage, name='manage'),

    # urls for reading posts
    url(r'^manage/published_posts$', views.manage_published_posts, {'page': 0}, name='manage_published_posts'),
    url(r'^manage/published_posts/(?P<page>\w+)$', views.manage_published_posts, name='manage_published_posts'),
    url(r'^manage/unpublished_posts$', views.manage_unpublished_posts, {'page': 0}, name='manage_unpublished_posts'),
    url(r'^manage/unpublished_posts/(?P<page>\w+)$', views.manage_unpublished_posts, name='manage_unpublished_posts'),

    # urls for creating posts
    url(r'^manage/create_link_post$', views.create_link_post, name='create_link_post'),
    url(r'^manage/create_status_post$', views.create_status_post, name='create_status_post'),
    url(r'^manage/create_photo_post$', views.create_photo_post, name='create_photo_post'),
    url(r'^manage/create_video_post$', views.create_video_post, name='create_video_post'),

    # auth
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^settings/password/$', views.password, name='password'),
    url(r'^oauth/', include('social_django.urls', namespace='social')),
    url(r'^admin/', admin.site.urls),
]
