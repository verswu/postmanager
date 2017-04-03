import re
import requests
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth import update_session_auth_hash, login, authenticate
from django.contrib import messages
from django.shortcuts import render, redirect

from social_django.models import UserSocialAuth
import facebook

from postmanagersite import settings
from .forms import BaseForm, LinkForm, PhotoForm, VideoForm

RAW_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DATE_FORMAT = '%d, %b %Y'
POST_IMPRESSIONS_ENDPOINT = 'https://graph.facebook.com/insights/post_impressions_unique'


def _get_graph_api(access_token):
    return facebook.GraphAPI(access_token=access_token, version='2.7')


@login_required
def home(request):
    fb_user = request.user.social_auth.get(provider='facebook')
    graph = _get_graph_api(fb_user.access_token)
    accounts = graph.get_connections(id='me', connection_name='accounts')['data']
    # set token and graph sdk for use for rest of site via session
    request.session['accounts'] = accounts
    return render(request, 'postmanager/home.html', {'accounts': accounts})


@login_required
def manage(request):
    # get page access token for the chosen page
    page_id = request.GET.get('id')
    page_dict = (account for account in request.session['accounts'] if account["id"] == page_id).next()
    request.session['page_id'] = page_id
    request.session['access_token'] = page_dict['access_token']
    request.session['name'] = page_dict['name']
    context = {
        'name': request.session['name'],
        'page_id': page_id,
    }
    return render(request, 'postmanager/manage.html', context)


def _get_post_insights(request, post_ids):
    # given list of post_ids, get insight objects for each
    insights_dict = {}
    url = "{}?access_token={}&ids={}".format(
        POST_IMPRESSIONS_ENDPOINT,
        request.session['access_token'],
        ','.join(post_ids)
    )
    insight_json = requests.get(url).json()
    for insight in insight_json:
        insights_dict[insight] = insight_json[insight]['data'][0]
    # ['values'][0]['value']
    return insights_dict


def _clean_posts(request, posts):
    # get a list of post ids get BATCH get insight objects for them
    post_ids = [post['id'] for post in posts]
    insights_dict = _get_post_insights(request, post_ids)

    page_id = request.session['page_id'] + '_'
    for post in posts:
        # remove page_id from post_id
        if str(post['id']).startswith(page_id):
            post['post_id'] = post['id'][len(page_id):]
        # format date, strip utc offset because it is not supported in python 2
        date_str = post['created_time']
        date_str = re.sub('[\+\-][0-9][0-9][0-9][0-9]$', '', date_str)
        post['created_time'] = datetime.strptime(date_str, RAW_DATE_FORMAT)
        # extract view count from insight dict
        post['view_count'] = insights_dict[post['id']]['values'][0]['value']


def _get_post_context(request, page, is_published):
    edge = 'promotable_posts'
    if is_published:
        edge = 'posts'
    # get page access token
    page_id = request.session['page_id']
    graph = _get_graph_api(request.session['access_token'])
    posts = graph.get_connections(
        id=page_id,
        connection_name=edge,
        fields='id,message,shares,story,is_published,created_time,status_type',
        is_published=is_published,
        limit=10,
        offset=10 * page)
    # clean posts before flattening it into a dict
    _clean_posts(request, posts['data'])
    return {
        'name': request.session['name'],
        'page_id': request.session['page_id'],
        'posts': posts['data'],
        'paging': posts['paging'],
        'current': page,
    }


def _get_has_next_context(request, context):
    additional_context = {
        'next': int(context['current']) + 1,
        'has_next': False,
        'previous': int(context['current']) - 1,
        'has_prev': False,
    }
    # check if response has next page, if so, check if it has data
    if (
        'paging' in context and
        'next' in context['paging']
    ):
        next_json = requests.get(context['paging']['next']).json()
        if next_json['data']:
            additional_context.update({'has_next': True})

    # check if response has previous page, if so, check if it has data
    if (
        additional_context['previous'] >= 0 and
        'paging' in context and
        'previous' in context['paging']
    ):
        prev_json = requests.get(context['paging']['previous']).json()
        if prev_json['data']:
            additional_context.update({'has_prev': True})
    return additional_context


@login_required
def manage_published_posts(request, page):
    context = _get_post_context(request, int(page), is_published=True)
    context.update(_get_has_next_context(request, context))
    return render(request, 'postmanager/manage_published_posts.html', context)


@login_required
def manage_unpublished_posts(request, page):
    context = _get_post_context(request, int(page), is_published=False)
    context.update(_get_has_next_context(request, context))
    return render(request, 'postmanager/manage_unpublished_posts.html', context)


def _get_common_published_form_context(request):
    return {
        'name': request.session['name'],
        'page_id': request.session['page_id'],
    }


def create_status_post(request):
    if request.method == 'POST':
        form = BaseForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            is_published = cleaned_data['is_published'] == 'True'
            graph = _get_graph_api(request.session['access_token'])
            graph.put_object(
                parent_object='me',
                connection_name='feed',
                message=cleaned_data['message'],
                published=is_published,
            )
            if is_published:
                return redirect('manage_published_posts')
            return redirect('manage_unpublished_posts')
    else:
        form = BaseForm()
    context = _get_common_published_form_context(request)
    context.update({
        'post_type': 'Status',
        'form': form,
    })
    return render(request, 'postmanager/form_base.html', context)


def create_link_post(request):
    form = LinkForm()
    if request.method == 'POST':
        form = LinkForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            is_published = cleaned_data['is_published'] == 'True'
            graph = _get_graph_api(request.session['access_token'])
            graph.put_object(
                parent_object='me',
                connection_name='feed',
                link=cleaned_data['link_url'],
                caption=cleaned_data['link_caption'],
                picture=cleaned_data['picture'],
                name=cleaned_data['link_name'],
                description=cleaned_data['link_description'],
                published=is_published,
            )
            if is_published:
                return redirect('manage_published_posts')
            return redirect('manage_unpublished_posts')
    context = _get_common_published_form_context(request)
    context.update({
        'post_type': 'Link',
        'form': form,
    })
    return render(request, 'postmanager/form_base.html', context)


def create_photo_post(request):
    if request.method == 'POST':
        form = PhotoForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            is_published = cleaned_data['is_published'] == 'True'
            graph = _get_graph_api(request.session['access_token'])
            graph.put_object(
                parent_object='me',
                connection_name='photos',
                message=cleaned_data['message'],
                url=cleaned_data['photo_url'],
                published=is_published,
            )
            if is_published:
                return redirect('manage_published_posts')
            return redirect('manage_unpublished_posts')
    else:
        form = PhotoForm()
    context = _get_common_published_form_context(request)
    context.update({
        'post_type': 'Photo',
        'form': form,
    })
    return render(request, 'postmanager/form_base.html', context)


def create_video_post(request):
    if request.method == 'POST':
        form = VideoForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            is_published = cleaned_data['is_published'] == 'True'
            graph = _get_graph_api(request.session['access_token'])
            graph.put_object(
                parent_object='me',
                connection_name='videos',
                message=cleaned_data['message'],
                file_url=cleaned_data['video_url'],
                title=cleaned_data['title'],
                published=is_published,
            )
            if is_published:
                return redirect('manage_published_posts')
            return redirect('manage_unpublished_posts')
    else:
        form = VideoForm()
    context = _get_common_published_form_context(request)
    context.update({
        'post_type': 'Video',
        'form': form,
    })
    return render(request, 'postmanager/form_base.html', context)

# ----- Everything below is boilerplate django facebook auth stuff ------- #


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password1')
            )
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def settings(request):
    user = request.user
    fb_user = user.social_auth.get(provider='facebook')
    graph = _get_graph_api(fb_user.access_token)
    accounts = graph.get_connections(id='me', connection_name='accounts')['data']
    # set token and graph sdk for use for rest of site via session
    request.session['accounts'] = accounts
    try:
        facebook_login = user.social_auth.get(provider='facebook')
    except UserSocialAuth.DoesNotExist:
        facebook_login = None

    can_disconnect = (user.social_auth.count() > 1 or user.has_usable_password())

    return render(request, 'postmanager/home.html', {
        'facebook_login': facebook_login,
        'can_disconnect': can_disconnect,
        'accounts': accounts,
    })


@login_required
def password(request):
    if request.user.has_usable_password():
        PasswordForm = PasswordChangeForm
    else:
        PasswordForm = AdminPasswordChangeForm

    if request.method == 'POST':
        form = PasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordForm(request.user)
    return render(request, 'core/password.html', {'form': form})
