import secrets
from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    key = models.CharField(max_length=200, default="")
    is_verified = models.BooleanField(default=False)
    is_member = models.BooleanField(default=False)

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    company_type = models.CharField(max_length=100, default="")

    wordpress_url = models.URLField(max_length=200, default="")
    wordpress_username = models.CharField(max_length=100, default="")
    wordpress_application_password = models.CharField(max_length=200, default="")
    
    stripe_customer_id = models.CharField(max_length=50, default="")
    stripe_subscription_id = models.CharField(max_length=50, default="")  

    membership_levels = {
        'none' : 'none',
        'Good' : 'Good',
        'Better' : 'Better',
        'Best' : 'Best'
    }

    membership_level = models.CharField(max_length=10, choices=membership_levels, default='none')
    has_paid = models.BooleanField(default=False)
    blogs_remaining = models.IntegerField(default=1)

    def __str__(self):
        return self.user.username
    
class Blog(models.Model):
    id = models.CharField(default=secrets.token_hex(20), max_length=20, primary_key=True)
    published = models.BooleanField(default=False)
    generated = models.BooleanField(default=False)

    docx_blog = models.FileField(upload_to="blogDocx")

    task_id = models.CharField(max_length=200, default="")
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="blogs")

    image = models.ImageField(upload_to="blogImages")
    title = models.CharField(max_length=200, default="")
    topic = models.CharField(max_length=200, default="")

    subheading_1 = models.CharField(max_length=200, default="")
    section_1 = models.TextField(default="")

    subheading_2 = models.CharField(max_length=200, default="")
    section_2 = models.TextField(default="")

    subheading_3 = models.CharField(max_length=200, default="")
    section_3 = models.TextField(default="")

    subheading_4 = models.CharField(max_length=200, default="")
    section_4 = models.TextField(default="")

    subheading_5 = models.CharField(max_length=200, default="")
    section_5 = models.TextField(default="")