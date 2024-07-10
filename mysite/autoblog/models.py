from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_member = models.BooleanField(default=False)

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    wordpress_url = models.URLField(max_length=200)
    wordpress_username = models.CharField(max_length=100)
    wordpress_application_password = models.CharField(max_length=200)
    
    stripe_customer_id = models.CharField(max_length=50)
    stripe_subscription_id = models.CharField(max_length=50)


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
    author = models.OneToOneField(Member, on_delete=models.CASCADE, primary_key=True)
    date = models.DateField(auto_now_add=True)
    
    # BLOG
    meta_keywords = models.CharField(max_length=100, default="")
    meta_description = models.CharField(max_length=200, default="")

    image = models.ImageField(upload_to="blogimages")
    title = models.CharField(max_length=200)

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
