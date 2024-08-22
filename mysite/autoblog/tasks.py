import openai
import requests
from io import BytesIO
from PIL import Image
import replicate
import base64
from celery import app
from openai import OpenAI
from celery import shared_task
from .models import User, Member, Blog, BlogSkeleton, BlogHistory, AutomatedBlogging
from datetime import timedelta
from .errors import BlogGenerationError
from django.utils.timezone import now
from redis import Redis
from django.core.files.base import ContentFile
from django.db.models import F, ExpressionWrapper, FloatField, Subquery
from .errors import BlogUploadError, ImageUploadError, ChangeFeaturedImageError, DeletingBlogError
from autoblog.blog_helper_methods import *

client = OpenAI()

@shared_task
def generate_blog_and_header_image(id='', username='', title='', generate_image="False"):
    user = User.objects.get(username=username)
    member = Member.objects.get(user=user)
    blog = Blog.objects.get(id=id)
    
    try:
        # Generate Blog's Image
        if generate_image == "True":
            generate_blog_image(username=username, title=title, blog=blog)

        # Generate Blog
        generate_blog(title=title, blog=blog)
        blog.generated = True
        blog.save()
    except BlogGenerationError as e:
        member.blogs_remaining += 1
        member.save()

        blog.image.delete()
        blog.delete()

        return False
    return True

@shared_task
def generate_blog_title_from_topic(id=''):
    try:
        blog_skeleton = BlogSkeleton.objects.get(id=id)
        title = generate_blog_title(blog_skeleton.topic)
        blog_skeleton.title = title
        blog_skeleton.generated = True
        
        blog_skeleton.save()

    except BlogSkeleton.DoesNotExist:
        pass

@shared_task
def generate_blog_from_title_or_topic(id='', username='', title_or_topic='', titles_or_topics='', generate_images="False"):
    user = User.objects.get(username=username)
    member = Member.objects.get(user=user)
    blog = Blog.objects.get(id=id)

    try:
        title = titles_or_topics
        if title_or_topic == "Topic":
            title = generate_blog_title(topic=titles_or_topics)
            blog.title = title
            blog.save()
        else:
            blog.title = title
            blog.save()

        # Generate Blog's Image
        if generate_images == "True":
            generate_blog_image(username=username, title=title, blog=blog)

        # Generate Blog
        generate_blog(title=title, blog=blog)
        blog.generated = True
        blog.save()

    except BlogGenerationError as e:
        member.blogs_remaining += 1
        member.save()

        blog.image.delete()
        blog.delete()

        return False
    return True

@shared_task
def automated_blog_posting():
    if AutomatedBlogging.objects.last().running:
        return False

    autoblog = AutomatedBlogging.objects.last()
    autoblog.running = True
    autoblog.save()

    members = Member.objects.filter(
        on_automated_plan=True, 
        automated_mode_on=True, 
        wordpress_linked=True
    ).annotate(
        days_since_last_pub=ExpressionWrapper(
            (now() - F("last_publish_date")) / timedelta(days=1), 
            output_field=FloatField()
        )
    ).filter(
        days_since_last_pub__gte=F("publish_date_ratio")
    )

    blogs = Blog.objects.filter(author__in=Subquery(members.values_list('pk', flat=True)), generated=True)
    blog_skeletons = BlogSkeleton.objects.filter(author__in=Subquery(members.values_list('pk', flat=True)), generated=True)

    for member in members:
        print(member.user.username, flush=True)
        member_blogs = blogs.filter(author=member)
        member_blog_skeletons = blog_skeletons.filter(author=member)

        # If member has generated blogs
        try:
            if member_blogs.count() > 0:
                print("Posting Blog", flush=True)

                blog = member_blogs.first()
                post_blog(blog=blog)
                member.last_publish_date = now()
            
            # If member has blog skeletons
            elif member_blog_skeletons.count() > 0 and member.blogs_remaining > 0:
                print("Generating from Blog Skeleton and Posting Blog", flush=True)
                blog_skeleton = member_blog_skeletons.first()
                generate_and_post_blog_to_wordpress(member=member, blog_skeleton=blog_skeleton)
                member.last_publish_date = now()

            # If member has nothing
            elif member.blogs_remaining > 0:
                print("Generating Blog From Scratch", flush=True)
                generate_and_post_blog_to_wordpress(member=member)
                member.last_publish_date = now()

            member.save()
        except BlogUploadError:
            continue

    
    autoblog.running = False
    autoblog.save()

    return True


# Post blog to WordPress
def post_blog(blog=None):
    member = blog.author

    # Get member's WordPress information
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
        raise BlogUploadError
    except ImageUploadError as e:
       raise BlogUploadError
    except ChangeFeaturedImageError as e:
       raise BlogUploadError
    
    blog_histories = BlogHistory.objects.filter(author=member)
    if blog_histories.count() >= 10:
        blog_histories.last().delete()
    
    # Create a blog history entry
    blog_history = BlogHistory.objects.create(author=member, title=blog.title, wordpress_post_id=post_id)
    blog_history.save()

    blog.image.delete()
    blog.delete()

def generate_and_post_blog_to_wordpress(member, blog_skeleton=None):    
    blog = Blog.objects.create(author=member)
    try:
        if not blog_skeleton:
            title = generate_blog_title(topic=member.company_type)
            blog.title = title
            generate_blog(title=title, blog=blog)
            generate_blog_image(username=member.user.username, title=title, blog=blog)
        else:
            if blog_skeleton.title == "":
                title = generate_blog_title(topic=blog_skeleton.topic)
            else:
                title = blog_skeleton.title

            blog.title = title
            generate_blog(title=title, blog=blog)
            if blog_skeleton.generate_ai_image:
                generate_blog_image(username=member.user.username, title=blog_skeleton.title, blog=blog)

            blog_skeleton.delete()

        member.blogs_remaining -= 1
        member.save()

        blog.generated = True
        blog.save()
    except openai.APIError as e:
        print(e, flush=True)

        member.blogs_remaining += 1
        member.save()
        blog.delete()
    except BlogGenerationError:
        member.blogs_remaining += 1
        member.save()
        blog.delete()
    
    try:
        post_blog(blog=blog)
    except BlogUploadError:
        raise BlogUploadError


# HELPER METHODS:
#########################################################################################
def generate_blog(title='', blog=None):
    try:
        outline = write_blog_outline(title=title)
        sections = ["first", "second", "third", "fourth", "concluding"]
        content = ""
        for i, section in enumerate(sections, start=1):
            blog_subheading = write_subheading(section=section, outline=outline, blog=content)
            blog_section = write_section(section=section, subheading=blog_subheading, outline=outline, blog=content)
            content += f"{section} subheading: {blog_subheading} {section} section: {blog_section}"

            setattr(blog, f"subheading_{i}", blog_subheading)
            setattr(blog, f"section_{i}", blog_section) 
        
        blog.task_id = ""
        blog.save()
    except openai.APIError as e:
        print(e, flush=True)
        raise BlogGenerationError("Error generating blog")

def generate_blog_image(username='', title='', blog=None):
    try:
        # Generate Image

        # Using Dalle 3
        # image_url = generate_image_dalle3(title=title)

        # Using Flux Schnell
        image_prompt = generate_image_description(title=title)
        image_url = generate_image_flux_schnell(image_prompt=image_prompt)

        # Read in image
        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))
        image = image.resize((600, 600))

        # Convert to WEBP
        webp_image = BytesIO()
        image.save(webp_image, "webp")
        webp_image.seek(0)

        # Save image
        blog.image.save(f"{username}_blog_header_image.webp", ContentFile(webp_image.read()), save=True)
    except openai.APIError as e:
        print(e, flush=True)
        raise BlogGenerationError("Error generating blog image")
    except Exception as e:
        raise BlogGenerationError("Error generating blog image")


# CALLS TO OPENAI API:
#########################################################################################
def generate_image_dalle3(title=''):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Generate a header image for a blog titled: {title}. Do not include \
        text in the image.",
        size="1024x1024",
        quality="standard",
    )

    image_url = response.data[0].url
    return image_url

def generate_image_flux_schnell(image_prompt=""):    
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input= {
           "prompt" : image_prompt + "DO NOT include text in the generated image."
        }
    )

    image_url = output[0]    
    return image_url

def generate_image_description(title=''):
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{'role':'user', "content" : f"Using this example response: Photo of \
                rolling sand dunes illuminated by the soft light of dusk. Capture \
                the scene from a low angle to emphasize the sweeping curves and \
                patterns of the dunes, with the sun setting on the horizon. The \
                warm colors of the sky contrast with the cool shadows on the sand, \
                creating a captivating play of light and texture. Use a wide-angle \
                lens to include the vast expanse of the desert landscape, with a \
                focus on the intricate patterns formed by the wind. generate a \
                similar prompt for a blog titled: {title}. Do not say to include \
                text or specifics in this prompt." }])
    outline = completion.choices[0].message.content
    return outline

def generate_blog_title(topic=''):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. \
                You are an expert copywriter who creates blog titles for a living. \
                You have a friendly tone of voice. You have a conversational writing \
                style. Create an engaging and SEO optimized title for a blog covering \
                the topic: {topic}. Please only write the title of the blog DO NOT \
                put the title in quotation marks. Write these titles for a five \
                section blog."}])
    title = completion.choices[0].message.content
    return title



def write_blog_outline(title=''):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. \
                   You are an expert copywriter who creates blog outlines for a living. \
                   You have a friendly tone of voice. You have a conversational writing \
                   style. Create a long form content outline in english for the blog \
                   post titled {title}. The content outline should include a minimum of \
                   5 subheadings and headings. The outline should be extensive and should \
                   cover the entire topic. Create detailed subheadings that are engaging. \
                   Do not write the blog post. Please only write the outline of the blog \
                   post. Please do not number the headings. Please add newline space \
                   between headings and subheadings. Do not self reference. Do not \
                   explain what you are doing"}])
    outline = completion.choices[0].message.content
    return outline

def write_subheading(section='', outline='', blog=''):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. \
                    You are an expert copywriter who creates blog subheadings for a \
                    living. You have a friendly tone of voice. You have a conversational \
                    writing style. Using this blog outline: {outline} and the current \
                    content of the blog: {blog}, write the {section} subheading for this \
                    blog. Make sure this subheading is SEO optimized and keep this \
                    subheading to at most 10 words. EXCLUDE any numbers of dashes \
                    from this subheading."}])
    generated_subheading = completion.choices[0].message.content
    return generated_subheading

def write_section(section='', subheading='', outline='', blog=''):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. \
                    You are an expert copywriter who creates blog paragraphs for a \
                    living. You have a friendly tone of voice. You have a conversational \
                    writing style. Using this blog outline: {outline} and the subheading \
                    {subheading} and the current content of the blog: {blog} write the \
                    {section} content section for this blog. Do NOT include the name of \
                    this subheading in this section. Keep this section between 100 and \
                    150 words. Also use language that an 8th grader can understand. \
                    Make sure it is SEO optimized."}])
    generated_section = completion.choices[0].message.content
    return generated_section 