from django import forms

TRUE_FALSE_CHOICES = (
    (True, "Yes"),
    (False, "No")
)

CTA_CHOICES = (
    ('SHOP_NOW', 'Shop Now'),
    ('BOOK_TRAVEL', 'Book Travel'),
    ('LEARN_MORE', 'Learn More'),
    ('SIGN_UP', 'Sign Up'),
    ('DOWNLOAD', 'Download'),
    ('INSTALL_MOBILE_APP', 'Install Mobile App'),
    ('USE_MOBILE_APP', 'Use Mobile App'),
    ('WATCH_VIDEO', 'Wach Video'),
    ('WATCH_MORE', 'Watch More'),
    ('OPEN_LINK', 'Open Link'),
)


class BaseForm(forms.Form):
    is_published = forms.ChoiceField(
        choices=TRUE_FALSE_CHOICES,
        label="This post will be published",
        initial='',
        widget=forms.Select(),
        required=True,
    )
    message = forms.CharField(
        label="Post text",
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 60}),
        required=True,
    )


class LinkForm(BaseForm):
    link_url = forms.URLField(label="URL")

    # TODO: CTA deprecated because it does not support unpublished posts. Implement it for published posts
    '''
    cta = forms.ChoiceField(
        choices=CTA_CHOICES,
        label="Call to Action",
        initial='',
        widget=forms.Select(),
        required=False,
    )
    '''
    link_name = forms.CharField(required=False,)
    link_caption = forms.CharField(required=False,)
    link_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 60}),
        required=False,
    )
    picture = forms.URLField(label="Picture URL")
    # TODO include photo and video upload


class PhotoForm(BaseForm):
    # TODO add file upload
    photo_url = forms.URLField()


class VideoForm(BaseForm):
    # TODO add video upload
    title = forms.CharField()
    video_url = forms.URLField()
