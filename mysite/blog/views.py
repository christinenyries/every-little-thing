import datetime

from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect, reverse

from taggit.models import Tag

from .models import Post, Comment
from .forms import CommentForm, SearchForm


def post_list(request, tag_slug=None, year=None, month=None):
    posts = Post.published.all()
    date = None
    tag = None

    # Filter posts by year and month
    if year and month:
        date = datetime.datetime(year, month, day=1)
        posts = posts.filter(publish__year=date.year, publish__month=date.month)
    # Filter posts by tag
    elif tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts = posts.filter(tags__in=[tag])

    # Filter posts by query
    search_form = SearchForm()
    query = None
    if "query" in request.GET:
        search_form = SearchForm(request.GET)
        if search_form.is_valid():
            query = search_form.cleaned_data["query"]
            posts = (
                posts.annotate(similarity=TrigramSimilarity("title", query))
                .filter(similarity__gt=0.1)
                .order_by("-similarity")
            )
        else:
            raise Http404("Invalid search")

    total_results = posts.count()

    # Pagination
    paginator = Paginator(posts, 4)
    page = request.GET.get("page")
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        if request.is_ajax():
            return HttpResponse("")
        posts = paginator.page(paginator.num_pages)

    if request.is_ajax():
        return render(
            request,
            "blog/post/list_ajax.html",
            {
                "posts": posts,
            },
        )
    return render(
        request,
        "blog/post/list.html",
        {
            "tag": tag,
            "date": date,
            "posts": posts,
            "query": query,
            "search_form": search_form,
            "total_results": total_results,
        },
    )


def post_detail(request, year, month, day, post):
    if "query" in request.GET:
        redirect(reverse("blog:post_list") + "?query=" + request.GET.get("query"))

    post = get_object_or_404(
        Post,
        slug=post,
        publish__lte=timezone.now(),
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    similar_posts = post.get_similar_posts()

    comments = post.get_active_comments()
    new_comment = None
    if request.method == "POST":
        comment_form = CommentForm(data=request.POST, post=post)
        if comment_form.is_valid():
            new_comment.save()
            messages.success(
                request, "Your comment has been successfully added to this post."
            )
    else:
        comment_form = CommentForm(post={})

    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "new_comment": new_comment,
            "search_form": SearchForm(),
            "comment_form": comment_form,
            "similar_posts": similar_posts,
        },
    )