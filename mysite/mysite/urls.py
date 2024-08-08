"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from autoblog import auth_views, member_views, stripe_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', member_views.home, name='home'),
    path('home/', member_views.home, name='home'),
    path('register/', auth_views.register, name='register'),
    path('login/', auth_views.login, name='login'),
    path('logout/', auth_views.logout, name='logout'),
    path('verification/', auth_views.verification, name='verification'),
    path('verifyEmail/<str:key>/', auth_views.verify_email, name='verify_email'),
    path('memberInfo/', member_views.member_info, name='member_info'),
    path('generateBlog/', member_views.generate_blog, name='generate_blog'),
    path('memberDash/', member_views.member_dashboard, name='member_dashboard'),
    path('settings/', member_views.settings, name='settings'),
    path('contact/', member_views.contact, name='contact'),
    path('taskStatus/<str:task_id>/', member_views.poll_task_status, name='task_status'),


    path('saveBlog/<str:blog_id>', member_views.save_blog, name='save_blog'),
    path('postBlog/<str:blog_id>', member_views.post_blog, name='post_blog'),
    path('emailBlog/<str:blog_id>', member_views.email_blog, name='email_blog'),
    path('deleteBlog/<str:blog_id>', member_views.delete_blog, name='delete_blog'),
    path('uploadBlogImage/<str:blog_id>', member_views.upload_blog_image, name='upload_blog_image'),
    path('deleteBlogImage/<str:blog_id>', member_views.delete_blog_image, name='delete_blog_image'),



    path('pay/', stripe_views.pay, name='pay'),
    path('pay/create-checkout-session/', stripe_views.create_checkout_session, name='checkout'),
    path('pay/cancel-subscription/', stripe_views.handle_subscription_cancelled, name='cancel-subscription'),
    path('pay/upgrade-subscription/', stripe_views.handle_subscription_update, name='upgrade-subscription'),
    path('webhook/', stripe_views.stripe_webhook, name='webhook'),

    path('dashboard/', member_views.dashboard, name='dashboard'),
    path('getBlogInfo/<str:blog_id>', member_views.get_blog_info, name='get_blog_info'),
    path('displayBlog/<str:blog_id>', member_views.display_blog, name='display_blog'),
    path('displayBlogQueue/', member_views.display_blog_queue, name='display_blog_queue'),
    path('generateBlogBatch/', member_views.generate_blog_batch, name='generate_blog_batch'),





]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)