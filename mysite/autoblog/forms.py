from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import ModelForm, Form
from .models import User, Member, Blog

class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

class LoginForm(AuthenticationForm):
    class Meta:
        model = User

class MemberInfoForm(ModelForm):
    class Meta:
        model = Member
        fields = ["wordpress_url", "wordpress_username", "wordpress_application_password"]
        
class GenerateBlogForm(Form):
    generate_ai_image = forms.CharField()
    title = forms.CharField(max_length=200)

    fields = ["title", "generate_ai_image"]


class BlogForm(Form):
    title = forms.CharField(max_length=200)
    
    # BLOG
    subheading_1 = forms.CharField(max_length=200)
    section_1 = forms.CharField()

    subheading_2 = forms.CharField(max_length=200)
    section_2 = forms.CharField()

    subheading_3 = forms.CharField(max_length=200)
    section_3 = forms.CharField()

    subheading_4 = forms.CharField(max_length=200)
    section_4 = forms.CharField()

    subheading_5 = forms.CharField(max_length=200)
    section_5 = forms.CharField()
   

    class Meta:
        model = Blog

class ContactForm(Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

class CustomBlogImageForm(Form):
    image = forms.ImageField()



