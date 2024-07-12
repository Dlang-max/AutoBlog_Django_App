import os
import base64
import requests
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import EmailMessage
from .forms import MemberInfoForm, GenerateBlogForm, BlogForm, ContactForm
from .models import Member, Blog
from .decorators import member_required
from .tasks import generate_blog_and_header_image
from .errors import BlogUploadError, ImageUploadError, ChangeFeaturedImageError, DeletingBlogError

def home(request):
    """
    Handles HTTP requests and responses for the /home endpoint

    Args:
        request (HttpRequest): The GET HTTP request sent to the /home endpoint

    Returns:
        HttpResponse: The HTTP response sent back to the client. Renders home.html. 
    """    
    return render(request, "autoblog/home.html")


@login_required(login_url="/login")
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            host = os.environ.get("EMAIL_HOST_USER")
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]
            EmailMessage(subject + " : " + name, message, "host@yourbloggingassistant.com",[host], reply_to=[email]).send()
            return redirect("member_dashboard")
    
    return render(request, "autoblog/contact.html")

@login_required(login_url="/login")
def member_info(request):
    """
    Handles HTTP requests and responses for the /memberInfo endpoint

    Args:
        request (HttpRequest): The HTTP request sent to the /memberInfo endpoint. Can 
        either be a POST or GET request.
    Returns:
        HttpResponse: The HTTP response sent back to the client. This response will either
        rerender the MemberInfoForm or redirect the user to the /home endpoint.

    """
    
    if request.method == "POST":
        form = MemberInfoForm(request.POST)
        if form.is_valid():
            user = request.user
            wordpress_url = form.cleaned_data["wordpress_url"]
            wordpress_username = form.cleaned_data["wordpress_username"]
            wordpress_application_password = form.cleaned_data["wordpress_application_password"]

            # Update a Member's Information
            member, created = Member.objects.get_or_create(user=user)

            if created:
                user.is_member = True

            member.wordpress_url = wordpress_url
            member.wordpress_username = wordpress_username
            member.wordpress_application_password = wordpress_application_password
            member.save()
            return redirect("member_dashboard")

    return render(request, "autoblog/memberInfo.html")


# HANDLE BLOG LOGIC
#=============================================================================#
# GENERATE BLOG
@login_required(login_url="/login")
def generate_blog(request):
    user = request.user

    try:
        member = Member.objects.get(user=user)
    except Member.DoesNotExist:
        member = Member.objects.create(user=user)
        member.save()
        user.is_member = True
        user.save()
    
    try:
        blog = Blog.objects.get(author=member)
        if blog:
            return redirect('/memberDash')
    except Blog.DoesNotExist:
        pass

    if request.method == "POST":
        form = GenerateBlogForm(request.POST)
        if form.is_valid():
            # Create and Save an empty Blog
            blog = Blog.objects.create(author=member)
            blog.save()

            username = request.user.username
            title = form.cleaned_data["title"]
            additional_info = form.cleaned_data["additional_info"]
            task = generate_blog_and_header_image.delay(username=username, title=title, addition_info=additional_info)

            member.blogs_remaining -= 1
            member.save()
            return redirect("/memberDash")
        
    return render(request, "autoblog/generateBlog.html", {"member": member})


@login_required(login_url="/login")
def member_dashboard(request):
    form = BlogForm()
    user = request.user
    try:
        member = Member.objects.get(user=user)
        blog = Blog.objects.get(author=member)
        return render(request, "autoblog/memberDashboard.html", {"blog" : blog, "member" : member, "form" : form})
    except Member.DoesNotExist:
        member = Member.objects.create(user=user)
        member.save()
        user.is_member = True
        user.save()
    except Blog.DoesNotExist:
        pass
    return render(request, "autoblog/memberDashboard.html", {"member" : member, "form" : form})

# SAVE BLOG
@login_required(login_url="/login")
@user_passes_test(member_required, login_url='member_info')
def save_blog(request):
    if request.method == 'POST':
        user = request.user
        member = Member.objects.get(user=user)
        try:
            blog = Blog.objects.get(author=member)
            form = BlogForm(request.POST)
            if form.is_valid():
                update_blog_in_db(form=form, blog=blog)
            else:
                blog.image.delete()
                blog.delete()
        except Blog.DoesNotExist:
            pass
    return redirect('/memberDash')

# POST BLOG
# BREAK DOWN INTO INDIVIDUAL HELPER METHODS
# ADD AS ASYNC TASK????
@login_required(login_url="/login")
@user_passes_test(member_required, login_url='member_info')
def post_blog(request):
    if request.method == 'POST':
        user = request.user
        member = Member.objects.get(user=user)

        form = BlogForm(request.POST)

        if form.is_valid():
            blog = Blog.objects.get(author=member)
            update_blog_in_db(form=form, blog=blog)
        else:
            # You break I delete
            blog.image.delete()
            blog.delete()
            return redirect("member_dashboard")

        # Get member's WordPress information
        member_wordpress_post_url = member.wordpress_url + "/wp-json/wp/v2/posts"
        member_wordpress_media_url = member.wordpress_url + "/wp-json/wp/v2/media"
        member_wordpress_username = member.wordpress_username
        member_wordpress_application_password = member.wordpress_application_password

        # Build HTTP Header for POSTing to WordPress REST API
        credentials = member_wordpress_username + ':' + member_wordpress_application_password
        token = base64.b64encode(credentials.encode())
        header = {"Authorization":"Basic " + token.decode("utf-8")}

        try:
            # Post Blog Content to WordPress
            post_id = post_blog_to_wordpress(member_wordpress_post_url=member_wordpress_post_url, header=header, blog=blog)
            member_wordpress_current_post_url = member_wordpress_post_url + '/' + str(post_id)

            # Get and Post Blog's header image to WordPress
            media_id = post_image_to_wordpress(member_wordpress_media_url=member_wordpress_media_url, header=header, blog=blog)

            # Update Blog's featured image
            update_blogs_featured_image(member_wordpress_current_post_url=member_wordpress_current_post_url, header=header, media_id=media_id)
            
        except BlogUploadError as e:
            return redirect("member_dashboard")
        except ImageUploadError as e:
            return redirect("member_dashboard")
        except ChangeFeaturedImageError as e:
            return redirect("member_dashboard")
        
        blog.image.delete()
        blog.delete()

    return redirect("member_dashboard")

# DELETE BLOG
@login_required(login_url='/login')
@user_passes_test(member_required, login_url='member_info')
def delete_blog(request):
    if request.method == 'POST':
        user = request.user
        member = Member.objects.get(user=user)
        try:
            blog = Blog.objects.get(author=member)
            blog.image.delete()
            blog.delete()
        except Blog.DoesNotExist:
            pass

    return redirect('/memberDash')

# HELPER METHODS
#############################################################################
def post_blog_to_wordpress(member_wordpress_post_url='', header='', blog=None):
    blog_content = format_blog(blog=blog)

    try:
        # Post Blog Content to WordPress
        post = {
            "title" : blog.title,
            "content" : blog_content,
            "status" : "publish",
        }
        post_response = requests.post(member_wordpress_post_url, headers=header, json=post)
        post_id = post_response.json().get("id")
    except requests.exceptions.ConnectionError:
        raise BlogUploadError("Error uploading blog to WordPress")
    return post_id

def post_image_to_wordpress(member_wordpress_media_url='', header='', blog=None):
    try:
        media = {
            'file': ('header_image.webp', blog.image, 'image/webp'),
            'status': 'publish'
        }
        media_response = requests.post(member_wordpress_media_url, headers=header, files=media)
        media_id = media_response.json().get('id')
    except requests.exceptions.ConnectionError:
        raise ImageUploadError("Error uploading image to WordPress")
    return media_id

def update_blogs_featured_image(member_wordpress_current_post_url='', header='', media_id=''):
    try:
        featured_payload = {
            'featured_media': media_id
        }
        # Update Blog's featured image
        requests.post(member_wordpress_current_post_url, headers=header, json=featured_payload)
    except requests.exceptions.ConnectionError:
        raise ChangeFeaturedImageError("Error changing blog's featured image")

def delete_blog_from_wordpress(member_wordpress_post_url='', header='', post_id=''):
    current_url = member_wordpress_post_url + f"/{post_id}"
    try:
        requests.delete(current_url, headers=header)
    except requests.exceptions.ConnectionError:
        raise DeletingBlogError("Error deleting blog")


def format_blog(blog):
    content = ""
    for i in range(1, 6):
        subheading = getattr(blog, f"subheading_{i}")
        section = getattr(blog, f"section_{i}")
        content += format_subheading_and_section(format_subheading(subheading), format_section(section))

    return f"<article style=\"font-family: Arial; display: flex; flex-direction: column; align-items: center;\">{content}</article>"

def format_title(title):
    title_html = f"<h2>{title}</h2>"
    return title_html

def format_subheading(subheading):
    subheading_html = f"<h3 style=\"text-align: center;\">{subheading}</h3>"    
    return subheading_html

def format_section(section):
    section_html = f"<p> &emsp; {section}</p>"
    return section_html

def format_subheading_and_section(subheading, section):
    subheading_and_section_html = f"<section style=\"display: flex; flex-direction: column; align-items: center;\">{subheading} {section}</section> "
    return subheading_and_section_html

def update_blog_in_db(form, blog):
    # Access blog content from POST request
    title = form.cleaned_data['title']
    blog.title = title

    for i in range(1, 6):
        subheading = form.cleaned_data[f"subheading_{i}"]
        section = form.cleaned_data[f"section_{i}"]

        setattr(blog, f"subheading_{i}", subheading)
        setattr(blog, f"section_{i}", section)     

    blog.save()