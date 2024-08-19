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

    # Automated Plan Information
    automated_mode_on = models.BooleanField(default=False)
    on_automated_plan = models.BooleanField(default=False)
    publish_date_ratio = models.FloatField(default=0.0)
    last_publish_date = models.DateTimeField(null=True)

    company_name = models.CharField(max_length=100, default="")
    company_type = models.CharField(max_length=100, default="")
    google_drive_folder_id = models.CharField(max_length=100, default="")

    wordpress_linked = models.BooleanField(default=False)
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
    id = models.CharField(default=secrets.token_hex(20), max_length=40, primary_key=True)

    docx_blog = models.FileField(upload_to="blogDocx")
    google_drive_blog_folder_id = models.CharField(max_length=100, default="")
    task_id = models.CharField(max_length=200, default="")

    generated = models.BooleanField(default=False)
    scheduled = models.BooleanField(default=False)
    published = models.BooleanField(default=False)

    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="blogs")

    image = models.ImageField(upload_to="blogImages")
    title = models.CharField(max_length=200, default="")

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

class BlogSkeleton(models.Model):
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="blog_skeletons")

    title = models.CharField(max_length=200, default="")
    topic = models.CharField(max_length=200, default="")
    generate_ai_image = models.BooleanField(default=False)

class BlogHistory(models.Model):
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="blog_history")

    title = models.CharField(max_length=200, default="")
    wordpress_post_id = models.CharField(max_length=100,default="")

class AutomatedBlogging(models.Model):
    running = models.BooleanField(default=False)