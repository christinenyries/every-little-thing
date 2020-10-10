import datetime

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User

from taggit.managers import TaggableManager


class PublishedManager(models.Manager):
    def get_queryset(self):
        return (
            super(PublishedManager, self)
            .get_queryset()
            .filter(publish__lte=timezone.now())
        )


class Post(models.Model):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique_for_date="publish")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blog_posts"
    )
    image = models.ImageField(upload_to="blog/post/img/%Y/%m/%d/", blank=True)
    body = models.TextField()
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # managers
    objects = models.Manager()
    published = PublishedManager()
    tags = TaggableManager()

    class Meta:
        ordering = ("-publish",)
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "blog:post_detail",
            args=[self.publish.year, self.publish.month, self.publish.day, self.slug],
        )

    def get_similar_posts(self):
        post_tags_ids = self.tags.values_list("id", flat=True)
        return (
            Post.published.filter(tags__in=post_tags_ids)
            .exclude(id=self.id)
            .annotate(same_tags=Count("tags"))
            .order_by("-same_tags", "-publish")[:4]
        )

    def get_active_comments(self):
        return self.comments.filter(active=True)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=80)
    email = models.EmailField()
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"Comment by {self.name} on {self.post}"
