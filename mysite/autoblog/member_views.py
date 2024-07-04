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
from .tasks import write_blog

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

            return redirect('member_dashboard')
    

    return render(request, "autoblog/contact.html")

@login_required(login_url="/login")
def member_info(request):
    """
    Handles HTTP requests and responses for the /memberInfo endpoint

    Args:
        request (HttpRequest): The HTTP request sent to the /memberIndo endpoint. Can 
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

            try:
                member = Member.objects.get(user=user)
                member.wordpress_url = wordpress_url
                member.wordpress_username = wordpress_username
                member.wordpress_application_password = wordpress_application_password
            except Member.DoesNotExist:
                member = Member.objects.create(user=user, wordpress_url=wordpress_url, 
                                wordpress_username=wordpress_username, 
                                wordpress_application_password=wordpress_application_password)
            member.save()
            user.is_member = True
            user.save()
            return redirect('/home')
        
    form = MemberInfoForm()
    return render(request, "autoblog/memberInfo.html", {"form" : form})


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
            task = write_blog.delay(username=username, title=title, addition_info=additional_info)

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
                blog.delete()
        except Blog.DoesNotExist:
            pass
    return redirect('/memberDash')

# POST BLOG
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
            blog.delete()
        
        member_wordpress_post_url = member.wordpress_url + "/wp-json/wp/v2/posts"
        member_wordpress_username = member.wordpress_username
        member_wordpress_application_password = member.wordpress_application_password

        # Build HTTP Header for POSTing to WordPress REST API
        credentials = member_wordpress_username + ':' + member_wordpress_application_password
        token = base64.b64encode(credentials.encode())
        header = {"Authorization":"Basic " + token.decode("utf-8")}

        # Get a User's Blog
        try:
            blog = Blog.objects.get(author=member)
        except Blog.DoesNotExist:
            return redirect("member_dashboard")


        # Format a User's Blog
        blog_content = format_blog(blog=blog)

        post = {
            "title" : blog.title,
            "content" : blog_content,
            "status" : "publish"
        }

        try:
            response = requests.post(member_wordpress_post_url, headers=header, json=post)
        except requests.exceptions.ConnectionError:
            return redirect("member_dashboard")
        
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
            blog.delete()
        except Blog.DoesNotExist:
            pass

    return redirect('/memberDash')

# HELPER METHODS
#############################################################################

def format_blog(blog):
    content = ""

    subheading_1 = blog.subheading_1
    section_1 = blog.section_1
    content += format_subheading_and_section(format_subheading(subheading_1), format_section(section_1))

    subheading_2 = blog.subheading_2
    section_2 = blog.section_2
    content += format_subheading_and_section(format_subheading(subheading_2), format_section(section_2))

    subheading_3 = blog.subheading_3
    section_3 = blog.section_3
    content += format_subheading_and_section(format_subheading(subheading_3), format_section(section_3))


    subheading_4 = blog.subheading_4
    section_4 = blog.section_4
    content += format_subheading_and_section(format_subheading(subheading_4), format_section(section_4))

    subheading_5 = blog.subheading_5
    section_5 = blog.section_5
    content += format_subheading_and_section(format_subheading(subheading_5), format_section(section_5))

    return f"<article style=\"font-family: Arial; display: flex; flex-direction: column; align-items: center;\">{content}</article>"


def format_title(title):
    title_html = f"<h2>{title}</h2>"
    return title_html

def format_subheading(subheading):
    subheading_html = f"<h3 style=\"text-align: center;\">{subheading}</h3>"    
    return subheading_html

def format_section(section):
    section_html = f"<p>{section}</p>"
    return section_html

def format_subheading_and_section(subheading, section):
    subheading_and_section_html = f"<section style=\"display: flex; flex-direction: column; align-items: center;\">{subheading} {section}</section> "
    return subheading_and_section_html


def update_blog_in_db(form, blog):
    # Access blog content from POST request
    title = form.cleaned_data['title']
    subheading_1 = form.cleaned_data['subheading_1']
    section_1 = form.cleaned_data['section_1']
    subheading_2 = form.cleaned_data['subheading_2']
    section_2 = form.cleaned_data['section_2']
    subheading_3 = form.cleaned_data['subheading_3']
    section_3 = form.cleaned_data['section_3']
    subheading_4 = form.cleaned_data['subheading_4']
    section_4 = form.cleaned_data['section_4']
    subheading_5 = form.cleaned_data['subheading_5']
    section_5 = form.cleaned_data['section_5']

    # Save updated blog
    blog.title = title
    blog.subheading_1 = subheading_1
    blog.section_1 = section_1
    blog.subheading_2 = subheading_2
    blog.section_2 = section_2
    blog.subheading_3 = subheading_3
    blog.section_3 = section_3
    blog.subheading_4 = subheading_4
    blog.section_4 = section_4
    blog.subheading_5 = subheading_5
    blog.section_5 = section_5
    blog.save()