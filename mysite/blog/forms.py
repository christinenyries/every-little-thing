from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop("post")
        super().__init__(*args, **kwargs)

    def save(self):
        comment = super().save(commit=False)
        comment.post = self.post
        comment.save()
        return comment

    class Meta:
        model = Comment
        fields = ("name", "email", "body")
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                }
            ),
        }


class SearchForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
    )
