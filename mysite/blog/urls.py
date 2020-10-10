from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    path("archive/<int:year>/<int:month>/", views.post_list, name="post_list_by_date"),
    path("tag/<slug:tag_slug>/", views.post_list, name="post_list_by_tag"),
    path(
        "<int:year>/<int:month>/<int:day>/<slug:post>/",
        views.post_detail,
        name="post_detail",
    ),
    path("", views.post_list, name="post_list"),
]