from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm

def register(request):
    """
    Handles HTTP requests and responses for the User registration endpoint /register
    If RegisterForm is valid, a new User gets created

    Args:
        request (HttpRequest): The HTTP request sent to the /register endpoint.
        Can either be a GET or a POST request.

    Returns:
        HttpResponse: The HTTP response sent back to the client. This response will 
        either render the RegisterForm for the user or redirect them to the /home
        endpoint after successfully registering.
    """ 
    if(request.user.is_authenticated):
        return redirect('/home')

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('/home')
        
    return render(request, "autoblog/register.html")


def login(request):
    """
    Handles HTTP requests and responses for the /login endpoint

    Args:
        request (HttpRequest): The HTTP request sent to the /login endpoint. Can either 
        be a POST or GET request
    
    Returns:
        HttpResponse: The HTTP response sent back to the client. This will either render 
        the User login form or login the user and redirect them to /home endpoint if a 
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

            if user is not None:
                auth_login(request=request, user=user)
                return redirect('/home')
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
    return redirect('/home')
