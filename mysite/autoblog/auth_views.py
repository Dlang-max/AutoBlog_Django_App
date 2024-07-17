from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from .forms import RegisterForm, LoginForm
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import HttpResponse
from .models import User
import secrets
import os

def register(request):
    """
    Handles HTTP requests and responses for the User registration endpoint /register
    If RegisterForm is valid, a new User gets created

    Args:
        request (HttpRequest): The HTTP request sent to the /register endpoint.
        Can either be a GET or a POST request.

    Returns:
        HttpResponse: The HTTP response sent back to the client. This response will 
        either render the RegisterForm for the user or redirect them to the generate_blog
        endpoint after successfully registering.
    """ 
    if(request.user.is_authenticated):
        return redirect("generate_blog")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            key = secrets.token_hex(64)

            user = form.save()
            user.key = key
            user.save()

            send_verification_email(email=email, key=key)
            return redirect("verification")
        else:
            form_errors_dict = form.errors.get_json_data(escape_html=True)
            error_key_list = list(form_errors_dict)
            error = form_errors_dict[str(error_key_list[0])][0]["message"]
            messages.add_message(request, messages.ERROR, error) 
    return render(request, "autoblog/register.html")

def send_verification_email(email='', key=''):
    host = os.environ.get("EMAIL_HOST_USER")
    subject = "Verification Email"
    html_message = render_to_string("autoblog/verifyEmail.html", {"key" : key})

    message = EmailMessage(subject=subject, body=html_message, from_email=host, to=[email])
    message.content_subtype = "html"
    message.send()

def verification(request):
    return render(request, "autoblog/verification.html")

@csrf_exempt
def verify_email(request, key):
    try:
        user = User.objects.get(key=key)
        user.is_verified = True
        user.save()
    except User.DoesNotExist:
        return redirect('login')
    return redirect('login')
    


def login(request):
    """
    Handles HTTP requests and responses for the /login endpoint

    Args:
        request (HttpRequest): The HTTP request sent to the /login endpoint. Can either 
        be a POST or GET request
    
    Returns:
        HttpResponse: The HTTP response sent back to the client. This will either render 
        the User login form or login the user and redirect them to generate_blog endpoint if a 
        user is successfully authenticated
    """
    if request.method == "POST":

        # FIGURE OUT WHY FORM IS NOT VALIDATING
        # takes in request and request.POST not just request.POST
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request=request, username=username, password=password)

            if user is not None and user.is_verified:
                auth_login(request=request, user=user)
                return redirect("generate_blog")
            else:
                return render(request, "autoblog/login.html")
    return render(request, "autoblog/login.html")


@login_required(login_url="/login")
def logout(request):
    """
    Handles HTTP requests and responses for the /logout endpoint

    Args:
        request (HttpRequest): The HTTP request sent to the /logout endpoint
    Returns:
        HttpResponse: The HTTP response sent back to the client. 
        Will logout the current user.
    """
    auth_logout(request)
    return redirect("home")
