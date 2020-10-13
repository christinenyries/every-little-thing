import datetime
import calendar

from django.utils import timezone
from django.shortcuts import reverse
from django.http import HttpResponse
from django.utils.text import slugify
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.template import Context, Template


from taggit.models import Tag

from .models import Post, Comment
from .forms import CommentForm, SearchForm


def create_post(title_text, days=0):
    publish = timezone.now() + datetime.timedelta(days=days)

    return Post.objects.create(
        title=title_text,
        slug=slugify(title_text),
        author=get_user_model().objects.get(username="author"),
        publish=publish,
    )


def create_comment(post, name, active=True):
    return Comment.objects.create(
        post=post,
        name=name,
        email="yourusername@example.com",
        body="Lorem ipsum",
        active=active,
    )


class PostListViewTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="author", password="1234")

    def test_no_posts(self):
        """
        Display appropriate message if no post exists.
        """
        response = self.client.get(reverse("blog:post_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing here.")
        self.assertQuerysetEqual(response.context.get("posts"), [])

    def test_future_post(self):
        """
        Do not display post whose publish date is in the future.
        """
        create_post("Future Post", days=30)
        response = self.client.get(reverse("blog:post_list"))
        self.assertContains(response, "Nothing here.")
        self.assertQuerysetEqual(response.context.get("posts"), [])

    def test_past_post(self):
        """
        Display a post published in the past.
        """
        create_post("Past Post", days=-30)
        response = self.client.get(reverse("blog:post_list"))
        self.assertQuerysetEqual(response.context.get("posts"), ["<Post: Past Post>"])

    def test_post_published_just_now(self):
        """
        Display a post published just now.
        """
        create_post("Past Post", days=0)
        response = self.client.get(reverse("blog:post_list"))
        self.assertQuerysetEqual(response.context.get("posts"), ["<Post: Past Post>"])

    def test_future_and_past_post(self):
        """
        Even if both future and past posts exist, only past posts are displayed.
        """
        create_post("Past Post", days=0)
        create_post("Future Post", days=30)
        response = self.client.get(reverse("blog:post_list"))
        self.assertQuerysetEqual(response.context.get("posts"), ["<Post: Past Post>"])

    def test_post_ordering(self):
        """
        Posts should be displayed in descending order of publish date.
        """
        create_post("One Day Ago Post", days=-1)
        create_post("Two Days Ago Post", days=-2)
        create_post("Three Days Ago Post", days=-3)
        response = self.client.get(reverse("blog:post_list"))
        self.assertQuerysetEqual(
            response.context.get("posts"),
            [
                "<Post: One Day Ago Post>",
                "<Post: Two Days Ago Post>",
                "<Post: Three Days Ago Post>",
            ],
        )

    def test_pagination_on_first_page(self):
        """
        First page should display 4 posts maximum even if existing posts are more than 4.
        """
        create_post("First Post", days=-5)
        create_post("Second Post", days=-4)
        create_post("Third Post", days=-3)
        create_post("Fourth Post", days=-2)
        create_post("Fifth Post", days=-1)

        response = self.client.get(reverse("blog:post_list"), {"page": "1"})
        self.assertEqual(len(response.context.get("posts")), 4)

    def test_pagination_with_invalid_page(self):
        """
        If page is not an integer, return first page
        """
        create_post("First Post", days=-5)
        create_post("Second Post", days=-4)
        create_post("Third Post", days=-3)
        create_post("Fourth Post", days=-2)
        create_post("Fifth Post", days=-1)

        response = self.client.get(reverse("blog:post_list"), {"page": "invalid"})
        self.assertEqual(len(response.context.get("posts")), 4)

    def test_pagination_with_last_page(self):
        """
        Last page should display last remaining posts.
        """
        # post on page 2 - last page
        create_post("First Post", days=-5)

        # posts on page 1
        create_post("Second Post", days=-4)
        create_post("Third Post", days=-3)
        create_post("Fourth Post", days=-2)
        create_post("Fifth Post", days=-1)

        response = self.client.get(reverse("blog:post_list"), {"page": "2"})
        self.assertEqual(len(response.context.get("posts")), 1)

    def test_pagination_with_out_of_range_page(self):
        """
        If page is out of range, return last page.
        """
        # post on page 2 - last page
        create_post("First Post", days=-5)

        # posts on page 1
        create_post("Second Post", days=-4)
        create_post("Third Post", days=-3)
        create_post("Fourth Post", days=-2)
        create_post("Fifth Post", days=-1)

        response = self.client.get(
            reverse("blog:post_list"),
            {"page": "3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context.get("posts")), 1)

    def test_ajax_pagination_with_out_of_range_page(self):
        """
        If request is ajax and page is out of range, return empty page.
        """
        # post on page 2 - last page
        create_post("First Post", days=-5)

        # posts on page 1
        create_post("Second Post", days=-4)
        create_post("Third Post", days=-3)
        create_post("Fourth Post", days=-2)
        create_post("Fifth Post", days=-1)

        response = self.client.get(
            reverse("blog:post_list"),
            {"page": "3"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.content, "")

    def test_query_posts_without_result(self):
        """
        If query doesn't match any posts, an appropriate message is displayed.
        """
        create_post("Some Post", days=-1)

        response = self.client.get(
            reverse("blog:post_list"),
            {"query": "qwe"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found 0 results")

    def test_query_posts_with_results(self):
        """
        Display posts that matched with the query.
        """
        create_post("Some Post", days=-1)

        response = self.client.get(
            reverse("blog:post_list"),
            {"query": "some"},
        )

        self.assertContains(response, "Found 1 result")
        self.assertQuerysetEqual(
            response.context.get("posts"),
            [
                "<Post: Some Post>",
            ],
        )

    def test_post_displayed_with_tags(self):
        """
        Post displayed should include its corresponding tags.
        """
        post = create_post("Post")
        post.tags.add("foo", "bar")
        post.save()

        response = self.client.get(reverse("blog:post_list"))
        self.assertContains(response, "foo")

    def test_post_displayed_with_pub_date(self):
        """
        Post displayed should include its date of publication.
        """
        post = create_post("Post")
        publish = post.publish
        response = self.client.get(reverse("blog:post_list"))

        self.assertContains(
            response,
            f"Published on {calendar.month_abbr[publish.month]}. {publish.day}, {publish.year}",
        )


class PostListByTagViewTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="author", password="1234")

    def test_tagged_posts_message(self):
        """
        An appropriate message should be displayed when posts are filtered by tag.
        """
        post = create_post("Tagged Post")
        post.tags.add("foo")
        post.save()

        response = self.client.get(
            reverse("blog:post_list_by_tag", kwargs={"tag_slug": "foo"})
        )
        self.assertContains(response, 'Posts tagged with "foo"')

    def test_posts_filtered_by_tag(self):
        """
        Show only the posts with the requested tag.
        """
        post = create_post("Post with Foo Tag")
        post.tags.add("foo")
        post.save()

        create_post("Post with Bar Tag")
        post.tags.add("bar")
        post.save()

        response = self.client.get(
            reverse("blog:post_list_by_tag", kwargs={"tag_slug": "foo"})
        )
        self.assertQuerysetEqual(
            response.context.get("posts"), ["<Post: Post with Foo Tag>"]
        )


class PostListByDateViewTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="author", password="1234")

    def render_template(self, string, context=None):
        context = context or {}
        context = Context(context)
        return Template(string).render(context)

    def test_archived_posts_message(self):
        """
        An appropriate message should be displayed when posts are filtered by date
        """

        post = create_post("Archived Post")
        year = post.publish.year
        month = post.publish.month

        response = self.client.get(
            reverse(
                "blog:post_list_by_date",
                kwargs={"year": year, "month": month},
            )
        )
        self.assertContains(
            response, f'Posts published on "{calendar.month_abbr[month]} {year}"'
        )

    def test_first_past_post_on_month(self):
        """
        If post is the first published post of the month, then add entry in the archived posts list.
        """

        post = create_post("First Post of the Month", days=-30)
        year = post.publish.year
        month = post.publish.month

        rendered = self.render_template("{% load blog_tags %}{% show_archives %}")
        self.assertEqual(
            '<ul class="list-unstyled">\n    \n        '
            "<li>\n            "
            f'<a href="/archive/{year}/{month}/">{year} {calendar.month_name[month]}</a>\n        '
            "</li>\n    \n"
            "</ul>",
            rendered,
        )

    def test_not_first_past_post_on_month(self):
        """
        If post is not the first published post of the month, then don't add a new entry in the archived posts list.
        """

        post = create_post("First Post of the Month", days=-30)
        create_post("Second Post of the Month", days=-30)
        create_post("Third Post of the Month", days=-30)
        create_post("Fourth Post of the Month", days=-30)

        year = post.publish.year
        month = post.publish.month

        rendered = self.render_template("{% load blog_tags %}{% show_archives %}")
        self.assertEqual(
            '<ul class="list-unstyled">\n    \n        '
            "<li>\n            "
            f'<a href="/archive/{year}/{month}/">{year} {calendar.month_name[month]}</a>\n        '
            "</li>\n    \n"
            "</ul>",
            rendered,
        )

    def test_first_future_post_on_month(self):
        """
        Even if post is the first post of the month, don't add it the archived posts list if it's still in draft.
        """
        create_post("First Post of the Month", days=30)

        rendered = self.render_template("{% load blog_tags %}{% show_archives %}")
        self.assertEqual(
            '<ul class="list-unstyled">\n    \n</ul>',
            rendered,
        )

    def test_two_posts_published_on_different_months(self):
        """
        If two posts are published on different months, then there should also be two entries in descending
        order in the archived posts list.
        """

        post1 = create_post("First Post of the First Month", days=-30)
        year1 = post1.publish.year
        month1 = post1.publish.month

        post2 = create_post("First Post of the Second Month", days=-60)
        year2 = post2.publish.year
        month2 = post2.publish.month

        rendered = self.render_template("{% load blog_tags %}{% show_archives %}")
        self.assertEqual(
            '<ul class="list-unstyled">\n    \n        '
            "<li>\n            "
            f'<a href="/archive/{year1}/{month1}/">{year1} {calendar.month_name[month1]}</a>\n        '
            "</li>\n    \n        "
            "<li>\n            "
            f'<a href="/archive/{year2}/{month2}/">{year2} {calendar.month_name[month2]}</a>\n        '
            "</li>\n    \n"
            "</ul>",
            rendered,
        )


class PostDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="author", password="1234"
        )

    def test_future_post(self):
        """
        If post is not yet published, then it shouldn't be displayed.
        """
        post = create_post("Future Post", days=30)
        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_past_post(self):
        """
        If post is already published, then display it on page.
        """
        post = create_post("Past Post", days=-30)
        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Past Post")
        self.assertEquals(response.context.get("post"), post)

    def test_no_similar_posts(self):
        """
        Show appropriate message if there are no similar posts yet.
        """
        post = create_post("Post", days=-30)
        post.tags.add("foo")
        post.save()

        similar_post = create_post("Similar Post", days=-31)
        similar_post.tags.add("bar")
        similar_post.save()

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertContains(response, "No similar posts yet.")
        self.assertQuerysetEqual(response.context.get("similar_posts"), [])

    def test_post_with_one_similar_post(self):
        """
        Show similar posts on page.
        """
        post = create_post("Post", days=-30)
        post.tags.add("foo")
        post.save()

        similar_post = create_post("Similar Post", days=-31)
        similar_post.tags.add("foo")
        similar_post.save()

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("similar_posts"), ["<Post: Similar Post>"]
        )

    def test_post_with_five_similar_posts(self):
        """
        Show maximum of four similar posts in descending order of publish date.
        """
        post = create_post("Post", days=-30)
        post.tags.add("foo")
        post.save()

        similar_post = create_post("First Similar Post", days=-31)
        similar_post.tags.add("foo")
        similar_post.save()

        similar_post = create_post("Second Similar Post", days=-32)
        similar_post.tags.add("foo")
        similar_post.save()

        similar_post = create_post("Third Similar Post", days=-33)
        similar_post.tags.add("foo")
        similar_post.save()

        similar_post = create_post("Fourth Similar Post", days=-34)
        similar_post.tags.add("foo")
        similar_post.save()

        similar_post = create_post("Fifth Similar Post", days=-35)
        similar_post.tags.add("foo")
        similar_post.save()

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("similar_posts"),
            [
                "<Post: First Similar Post>",
                "<Post: Second Similar Post>",
                "<Post: Third Similar Post>",
                "<Post: Fourth Similar Post>",
            ],
        )

    def test_similar_posts_with_multiple_same_tags(self):
        """
        Show similar post with more similar tags first even if the less similar post is published earlier.
        """
        post = create_post("Post", days=-30)
        post.tags.add("foo", "bar")
        post.save()

        similar_post = create_post("Similar Post", days=-31)
        similar_post.tags.add("foo")
        similar_post.save()

        similar_post = create_post("More Similar Post", days=-32)
        similar_post.tags.add("foo", "bar")
        similar_post.save()

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("similar_posts"),
            [
                "<Post: More Similar Post>",
                "<Post: Similar Post>",
            ],
        )

    def test_post_without_comment(self):
        """
        Show appropriate message if no comments are added yet.
        """
        post = create_post("Post", days=-30)
        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )
        self.assertContains(response, "No comments yet.")
        self.assertEqual(response.context.get("new_comment"), None)
        self.assertQuerysetEqual(response.context.get("comments"), [])

    def test_post_with_comment(self):
        """
        Display comment to a post on page.
        """
        post = create_post("Post")
        create_comment(post, "Juan")

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("comments"),
            [
                f"<Comment: Comment by Juan on {post}>",
            ],
        )

    def test_comments_order(self):
        """
        Order existing comments from latest to oldest.
        """
        post = create_post("Post")
        create_comment(post, "Juan")
        create_comment(post, "Mike")

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("comments"),
            [
                f"<Comment: Comment by Mike on {post}>",
                f"<Comment: Comment by Juan on {post}>",
            ],
        )

    def test_inactive_comment(self):
        """
        Don't show inactive comments on page.
        """
        post = create_post("Post")
        create_comment(post, "Juan", active=False)

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(response.context.get("comments"), [])

    def test_active_and_inactive_comment(self):
        """
        Even if both active and inactive comments exist, show only the active comments.
        """
        post = create_post("Post")
        create_comment(post, "Juan", active=False)
        create_comment(post, "Mike")

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("comments"), [f"<Comment: Comment by Mike on {post}>"]
        )

    def test_two_comments_from_same_author(self):
        """
        Display multiple comments from same author on page.
        """
        post = create_post("Post")
        create_comment(post, "Juan")
        create_comment(post, "Juan")

        response = self.client.get(
            reverse(
                "blog:post_detail",
                kwargs={
                    "year": post.publish.year,
                    "month": post.publish.month,
                    "day": post.publish.day,
                    "post": slugify(post.slug),
                },
            )
        )

        self.assertQuerysetEqual(
            response.context.get("comments"),
            [
                f"<Comment: Comment by Juan on {post}>",
                f"<Comment: Comment by Juan on {post}>",
            ],
        )


class CommentModelTest(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="author", password="1234")

    def test_string_representation(self):
        post = create_post("Post")
        comment = create_comment(post, "User")
        self.assertEqual(str(comment), f"Comment by {comment.name} on {post}")


class CommentFormTest(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="author", password="1234")
        self.post = create_post("Post")

    def test_init(self):
        CommentForm(post=self.post)

    def test_init(self):
        with self.assertRaises(KeyError):
            CommentForm()

    def test_valid_data(self):
        form = CommentForm(
            {
                "name": "User",
                "email": "yourusername@example.com",
                "body": "Lorem ipsum",
            },
            post=self.post,
        )
        self.assertTrue(form.is_valid())
        comment = form.save()
        self.assertEqual(comment.name, "User")
        self.assertEqual(comment.email, "yourusername@example.com")
        self.assertEqual(comment.body, "Lorem ipsum")
        self.assertEqual(comment.post, self.post)

    def test_blank_data(self):
        form = CommentForm({}, post=self.post)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                "name": ["This field is required."],
                "email": ["This field is required."],
                "body": ["This field is required."],
            },
        )


class SearchFormTest(TestCase):
    def test_valid_data(self):
        form = SearchForm({"query": "keyword"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["query"], "keyword")

    def test_blank_data(self):
        form = SearchForm()
        self.assertFalse(form.is_valid())