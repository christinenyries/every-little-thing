from django import template
from django.utils.safestring import mark_safe
import markdown
from ..models import Post

register = template.Library()


@register.inclusion_tag("blog/post/latest_posts.html")
def show_latest_posts(count=5):
    latest_posts = Post.published.order_by("-publish")[:count]
    return {"latest_posts": latest_posts}


@register.inclusion_tag("blog/post/archives.html")
def show_archives():
    dates = Post.published.dates("publish", "month", order="DESC")
    return {"dates": dates}


@register.filter(name="markdown")
def markdown_format(text):
    return mark_safe(markdown.markdown(text))
