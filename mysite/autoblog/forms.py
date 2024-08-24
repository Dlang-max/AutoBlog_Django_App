from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import ModelForm, Form
from .models import User, Member, Blog
from django_quill.fields import QuillFormField

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
    generate_ai_image = forms.CharField(max_length=100)
    title = forms.CharField(max_length=200)

    fields = ["title", "generate_ai_image"]




class BlogForm(Form):
    title = forms.CharField(max_length=200)
    content = forms.CharField(widget=forms.Textarea)





class ContactForm(Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

class CustomBlogImageForm(Form):
    image = forms.ImageField()



class GenerateBlogBatchForm(Form):
    CHOICES = [
        ('1', 'Titles'),
        ('2', 'Topics'),
    ]

    generate_ai_images = forms.CharField(max_length=100)
    title_or_topic = forms.ChoiceField(choices=CHOICES)
    titles_or_topics = forms.CharField(widget=forms.Textarea)

class RTEForm(Form):
    content = QuillFormField()



