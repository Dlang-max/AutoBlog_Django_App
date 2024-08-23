import os
import base64
import secrets
import requests
from PIL import Image
from io import BytesIO
from .models import Member, Blog, BlogSkeleton, BlogHistory
from django.http import JsonResponse
from datetime import datetime
from celery.result import AsyncResult
from .decorators import member_required
from django.core.mail import EmailMessage
from autoblog.convert_blog_to_docx import *
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.template.defaulttags import register
from .tasks import generate_blog_and_header_image, generate_blog_from_title_or_topic, generate_blog_title_from_topic
from autoblog.upload_blog_to_google_drive import GoogleDriveManager
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from autoblog.blog_helper_methods import *
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import MemberInfoForm, GenerateBlogForm, BlogForm, ContactForm, CustomBlogImageForm, GenerateBlogBatchForm, RTEForm
from .errors import BlogUploadError, ImageUploadError, ChangeFeaturedImageError, DeletingBlogError, GoogleDriveError

@login_required(login_url='/login')
def settings(request):
    user = request.user
    member, created = Member.objects.get_or_create(user=user)

    if created:
        user.is_member = True
        user.save()

    return render(request, "autoblog/settings.html", {"member" : member})

@login_required(login_url='/login')
@user_passes_test(member_required, login_url='member_info')
def toggle_automated_mode(request):
    if request.method == "POST":
        user = request.user
        try:
            member = Member.objects.get(user=user)

            if not member.on_automated_plan:
                return redirect("dashboard")
            
            if not member.automated_mode_on:
                member.automated_mode_on = True
                member.last_publish_date = datetime(1945, 8, 6, 12, 0, 0)
            else:
                member.automated_mode_on = False
            member.save()
        except Member.DoesNotExist:
            pass

    return redirect("dashboard")


@login_required(login_url='/login')
def dashboard(request):
    user = request.user
    member, created = Member.objects.get_or_create(user=user)

    if created:
        user.is_member = True
        user.save()
    try:
        blogs = Blog.objects.filter(author=member)
        blog_skeletons = BlogSkeleton.objects.filter(author=member)
        blog_history = BlogHistory.objects.filter(author=member).order_by("-id")
    except Blog.DoesNotExist:
        blogs = []
    except BlogSkeleton.DoesNotExist:
        blog_skeletons = []

    return render(request, "autoblog/dashboard.html", {"blogs" : blogs, "blog_skeletons" : blog_skeletons, "blog_history" : blog_history, "member" : member})

@login_required(login_url='/login')
def display_blog(request, blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)

    except Member.DoesNotExist:
        return redirect('dashboard')
    except Blog.DoesNotExist:
        return redirect('dashboard')
    
    form = BlogForm()
    return render(request, "autoblog/displayBlog.html", {"blog" : blog, "form" : form, "rte_form" : RTEForm(initial={"content" : blog.content})})

@login_required(login_url='/login')
def get_blog_info(request, blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return redirect("dashboard")

    # get elements of blog
    blog_info = {}
    blog_info['title'] = blog.title


    for i in range(1, 6):
        subheading = getattr(blog, f"subheading_{i}")
        blog_info[f"subheading_{i}"] = subheading

        section = getattr(blog, f"section_{i}")
        blog_info[f"section_{i}"] = section

    # return elements
    return JsonResponse(blog_info)

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
            EmailMessage(subject + " : " + name, message, "host@yourbloggingassistant.com", [host], reply_to=[email]).send()
            return redirect("dashboard")
    
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
    user = request.user
    member,  created = Member.objects.get_or_create(user=user)

    if created:
        user.is_member = True
        user.save()
    
    if request.method == "POST":
        form = MemberInfoForm(request.POST)
        if form.is_valid():
            wordpress_url = form.cleaned_data["wordpress_url"]
            wordpress_username = form.cleaned_data["wordpress_username"]
            wordpress_application_password = form.cleaned_data["wordpress_application_password"]

            member_wordpress_post_url = wordpress_url + "/wp-json/wp/v2/users/me"
            member_wordpress_username = wordpress_username
            member_wordpress_application_password = wordpress_application_password

            # Build HTTP Header for POSTing to WordPress REST API
            credentials = member_wordpress_username + ':' + member_wordpress_application_password
            token = base64.b64encode(credentials.encode())
            header = {"Authorization":"Basic " + token.decode("utf-8")}
                
            # Send test request to check if this is user's website
            if test_member_website_credentials(member_wordpress_post_url=member_wordpress_post_url, header=header):
                # Update Member Info
                member.wordpress_linked = True
                member.wordpress_url = wordpress_url
                member.wordpress_username = wordpress_username
                member.wordpress_application_password = wordpress_application_password
            else:
                member.wordpress_linked = False

            member.save()
            return redirect("member_info")

    return render(request, "autoblog/memberInfo.html", {"member" : member})


# HANDLE BLOG LOGIC
#=============================================================================#
# GENERATE BLOG
@login_required(login_url="/login")
def generate_blog(request):
    user = request.user
    member, created = Member.objects.get_or_create(user=user)
    if created:
        user.is_member = True
        user.save()

    if request.method == "POST":
        form = GenerateBlogForm(request.POST)
        if form.is_valid():
            username = request.user.username
            title = form.cleaned_data["title"]
            generate_image = request.POST.get("generate_ai_image", 'False')

            blog = Blog.objects.create(author=member)
            blog.title = title
            task = generate_blog_and_header_image.delay(id=blog.id, username=username, title=title, generate_image=generate_image)
            blog.task_id = task.id
            blog.save()

            member.blogs_remaining -= 1
            member.save()
            return redirect("display_blog", blog_id=blog.id)
        
    return render(request, "autoblog/generateBlog.html", {"member": member})


# GENERATE BLOG BATCH
@login_required(login_url="/login")
def generate_blog_batch(request):
    if request.method == "POST":
        user = request.user
        member, created = Member.objects.get_or_create(user=user)
        if created:
            user.is_member = True
            user.save()

        # Check if form is valid
        form = GenerateBlogBatchForm(request.POST)
        if form.is_valid():
            username = user.username
            generate_images = request.POST.get("generate_ai_images", 'False')
            title_or_topic = form.cleaned_data["title_or_topic"]
            title_or_topic = "Title" if title_or_topic == '1' else "Topic"
            titles_or_topics = form.cleaned_data["titles_or_topics"]

            lines = titles_or_topics.split('\n')
            
            # Generate blogs with celery task
            for line in lines[-100:]:
                if not line.strip():
                    continue
                elif member.blogs_remaining > 0:
                    # create blog
                    blog = Blog.objects.create(author=member)
                    task = generate_blog_from_title_or_topic.delay(id=blog.id, username=username, title_or_topic=title_or_topic, titles_or_topics=line, generate_images=generate_images)
                    blog.task_id = task.id
                    blog.save()

                    member.blogs_remaining -= 1
                    member.save()
                elif member.on_automated_plan:
                    # create blog skeleton
                    blog_skeleton = BlogSkeleton.objects.create(author=member)
                    blog_skeleton.generate_ai_image = True if generate_images == "True" else False

                    if title_or_topic == "Title":
                        blog_skeleton.title = line
                        blog_skeleton.generated = True
                    else:
                        blog_skeleton.topic = line
                        generate_blog_title_from_topic.delay(id=blog_skeleton.id)
                    blog_skeleton.save()

        return redirect("dashboard")


    return render(request, "autoblog/generateBatch.html")


@csrf_exempt
def poll_task_status(request, task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_status" : task_result.status
    }

    return JsonResponse(result, status=200)

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
def save_blog(request, blog_id):
    if request.method == 'POST':
        try:
            blog = Blog.objects.get(id=blog_id)
            form = BlogForm(request.POST)
            if form.is_valid():
                update_blog_in_db(form=form, blog=blog)
            else:
                blog.image.delete()
                blog.delete()
        except Blog.DoesNotExist:
            pass
    return redirect("display_blog", blog_id=blog.id)


@login_required(login_url="/login")
@user_passes_test(member_required, login_url='member_info')
def email_blog(request, blog_id):
    user = request.user

    if request.method == "POST":
        try:
            member = Member.objects.get(user=user)

            # SAVE BLOG TO DB
            blog = Blog.objects.get(id=blog_id)
            form = BlogForm(request.POST)
            if form.is_valid():
                update_blog_in_db(form=form, blog=blog)

            # UPDATE BLOG .DOCX FILE
            update_blog_docx_file(user, blog)

            # UPLOAD .DOCX FILE TO GOOGLE DRIVE
            try:
               blog_folder_id = upload_blog_to_google_drive(user, member, blog)
            except GoogleDriveError:
                print("Error uploading blog to Google Drive")

            # EMAIL MEMBER WITH LINK TO BLOG FOLDER
            send_google_drive_link_email(email=user.email, key=blog_folder_id)

        except Blog.DoesNotExist:
            return redirect("dashboard")
        
        return redirect("display_blog", blog_id=blog.id)
    return redirect("dashboard")


# WORDPRESS API METHODS
#==================================================================================================
# POST BLOG
@login_required(login_url="/login")
@user_passes_test(member_required, login_url='member_info')
def post_blog(request, blog_id):
    if request.method == 'POST':
        user = request.user
        member = Member.objects.get(user=user)

        form = BlogForm(request.POST)

        if form.is_valid():
            try:
                blog = Blog.objects.get(id=blog_id)
                update_blog_in_db(form=form, blog=blog)
            except Blog.DoesNotExist:
                return redirect("dashboard")
        else:
            # You break I delete
            blog.image.delete()
            blog.delete()
            return redirect("dashboard")

        # Get member's WordPre  ss information
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
            if blog.image:
                media_id = post_image_to_wordpress(member_wordpress_media_url=member_wordpress_media_url, header=header, blog=blog)

                # Update Blog's featured image
                update_blogs_featured_image(member_wordpress_current_post_url=member_wordpress_current_post_url, header=header, media_id=media_id)
            
        except BlogUploadError as e:
            return redirect("dashboard")
        except ImageUploadError as e:
            return redirect("dashboard")
        except ChangeFeaturedImageError as e:
            return redirect("dashboard")
        
        blog_histories = BlogHistory.objects.filter(author=member).order_by('-id')
        if blog_histories.count() >= 10:
            blog_histories.last().delete()
        
        # Create a blog history entry
        blog_history = BlogHistory.objects.create(author=member, title=blog.title, wordpress_post_id=post_id)
        blog_history.save()

        blog.image.delete()
        blog.delete()

    return redirect("dashboard")


# DELETE BLOG FROM WORDPRESS
@login_required(login_url="/login")
@user_passes_test(member_required, login_url='member_info')
def delete_wordpress_blog(request, wordpress_post_id):
    try:
        user = request.user
        member = Member.objects.get(user=user)
        blog = BlogHistory.objects.filter(author=member).get(wordpress_post_id=wordpress_post_id)

        member_wordpress_post_url = member.wordpress_url + "/wp-json/wp/v2/posts"
        member_wordpress_username = member.wordpress_username
        member_wordpress_application_password = member.wordpress_application_password

        # Build HTTP Header for POSTing to WordPress REST API
        credentials = member_wordpress_username + ':' + member_wordpress_application_password
        token = base64.b64encode(credentials.encode())
        header = {"Authorization":"Basic " + token.decode("utf-8")}

        try:
            delete_blog_from_wordpress(member_wordpress_post_url=member_wordpress_post_url, header=header, post_id=blog.wordpress_post_id)
            blog.delete()

        except DeletingBlogError:
            pass
    except BlogHistory.DoesNotExist:
        pass

    return redirect("dashboard")

# UPLOAD CUSTOM BLOG IMAGE
@login_required(login_url='/login')
@user_passes_test(member_required, login_url='member_info')
def upload_blog_image(request, blog_id):
    if request.method == "POST":
        form = CustomBlogImageForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user

            image = form.cleaned_data["image"]
            image = Image.open(image)
            webp_image = BytesIO()
            image.save(webp_image, "webp")
            webp_image.seek(0)

            try:
                blog = Blog.objects.get(id=blog_id)
                blog.image.save(f"{user.username}_blog_header_image.webp", ContentFile(webp_image.read()), save=True)
            except Blog.DoesNotExist:
                pass    

    return redirect('display_blog', blog_id=blog.id)

# DELETE BLOG IMAGE
@login_required(login_url='/login')
@user_passes_test(member_required, login_url='member_info')
def delete_blog_image(request, blog_id):
    if request.method == "POST":
        try:
            blog = Blog.objects.get(id=blog_id)
            blog.image.delete()
        except Blog.DoesNotExist:
            pass

    return redirect('display_blog', blog_id=blog.id)

# DELETE BLOG
@login_required(login_url='/login')
@user_passes_test(member_required, login_url='member_info')
def delete_blog(request, blog_id):
    if request.method == 'POST':
        try:
            blog = Blog.objects.get(id=blog_id)
            blog.image.delete()
            blog.delete()
        except Blog.DoesNotExist:
            pass

    return redirect("dashboard")



# HELPER METHODS
#############################################################################
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

def update_blog_docx_file(user, blog):
    document = Document()

    # Add image to docx file
    if blog.image:
        image = Image.open(blog.image)
        image = image.convert("RGB")
        byte_io = BytesIO()
        image.save(byte_io, format="JPEG")
        add_image(document, byte_io)

    # Add blog content to docx file
    add_title(document, blog.title)
    for i in range(1, 6):
        subheading = getattr(blog, f"subheading_{i}")
        add_subheading(document, subheading)
        section = getattr(blog, f"section_{i}")
        add_paragraph(document, section)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    if blog.docx_blog:
        blog.docx_blog.delete()

    blog.docx_blog.save(f"{user.username}_blog.docx", content=buffer)


def upload_blog_to_google_drive(user, member, blog):
    manager = GoogleDriveManager()

    # Upload Client Folder to Google Drive 
    member_folder_id = member.google_drive_folder_id
    if member_folder_id == '' or not manager.folder_exists(member_folder_id):
        member_folder_id = manager.create_folder(folder_name=user.email)

        if member_folder_id:
            member.google_drive_folder_id = member_folder_id
            manager.share_folder(folder_id=member.google_drive_folder_id, user_email=user.email)
            member.save()

    # Upload Blog to Google Drive
    blog_folder_id = blog.google_drive_blog_folder_id
    if blog_folder_id != "" and manager.folder_exists(blog_folder_id):
        manager.delete_folder(blog_folder_id)

    blog_folder_id = manager.create_folder(folder_name=blog.title, parent_folder_id=member.google_drive_folder_id)
    if blog_folder_id:
        blog.google_drive_blog_folder_id = blog_folder_id
        blog.save()

        if blog.image:
            manager.create_image_file(parent_folder_id=blog.google_drive_blog_folder_id, file_name="image", file_path=blog.image.path)
        manager.create_docx_file(parent_folder_id=blog.google_drive_blog_folder_id, file_name="blog", file_path=blog.docx_blog.path)

    return blog_folder_id


def send_google_drive_link_email(email='', key=''):
    host = os.environ.get("EMAIL_HOST_USER")
    subject = "Google Docs Blog"
    html_message = render_to_string("autoblog/googleDriveLink.html", {"key" : key})

    message = EmailMessage(subject=subject, body=html_message, from_email=host, to=[email])
    message.content_subtype = "html"
    message.send()