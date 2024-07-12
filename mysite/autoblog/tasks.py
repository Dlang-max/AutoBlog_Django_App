import openai
import requests
from io import BytesIO
from PIL import Image
from celery import app
from openai import OpenAI
from celery import shared_task
from .errors import BlogGenerationError
from .models import User, Member, Blog
from django.core.files.base import ContentFile



client = OpenAI()
@shared_task
def generate_blog_and_header_image(username=None, title='', addition_info=''):
    user = User.objects.get(username=username)
    member = Member.objects.get(user=user)
    blog = Blog.objects.get(author=member)

    try:
        # Generate Blog's Image
        generate_blog_image(username=username, title=title, blog=blog)

        # Generate Blog
        generate_blog(title=title, blog=blog)

    except BlogGenerationError as e:
        member.blogs_remaining += 1
        blog.image.delete()
        blog.delete()
        return False
    return True


# HELPER METHODS:
##################################################################################################
def generate_blog(title='', blog=None):
    try:
        outline = write_blog_outline(title=title)
        blog.title = title
        sections = ["first", "second", "third", "fourth", "concluding"]

        for i, section in enumerate(sections, start=1):
            blog_subheading = write_subheading(section=section, outline=outline)
            blog_section = write_section(section=section, outline=outline)

            setattr(blog, f"subheading_{i}", blog_subheading)
            setattr(blog, f"section_{i}", blog_section) 

    except openai.APIError as e:
        raise BlogGenerationError("Error generating blog")



def generate_blog_image(username='', title='', blog=None):
    try:
        # Generate Image
        image_url = generate_image(title=title)

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
        raise BlogGenerationError("Error generating blog image")

# CALLS TO OPENAI API:
##################################################################################################
def generate_image(title=''):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Generate a header image for a blog titled: {title}. Do not include text in the image.",
        size="1024x1024",
        quality="standard",
    )

    image_url = response.data[0].url
    return image_url

def write_blog_outline(title=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog outlines for a living. You have a friendly tone of voice. You have a conversational writing style. Create a long form content outline in english for the blog post titled {title}. The content outline should include a minimum of 5 subheadings and headings. The outline should be extensive and should cover the entire topic. Create detailed subheadings that are engaging. Do not write the blog post. Please only write the outline of the blog post. Please do not number the headings. Please add newline space between headings and subheadings. Do not self reference. Do not explain what you are doing"}]
    )
    outline = completion.choices[0].message.content
    return outline

def write_subheading(section='', outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog subheadings for a living. You have a friendly tone of voice. You have a conversational writing style. Using this blog outline: {outline}, write the {section} subheading for this blog. Make sure this subheading is SEO optimized and keep this subheading to at most 10 words. EXCLUDE any numbers of dashes from this subheading."}]
    )
    generated_subheading = completion.choices[0].message.content
    return generated_subheading

def write_section(section='', subheading='', outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog paragraphs for a living. You have a friendly tone of voice. You have a conversational writing style. Using this blog outline: {outline} and the subheading {subheading}, write the {section} content section for this blog. Do NOT include the name of this subheading in this section. Keep this section between 100 and 150 words. Also use language that an 8th grader can understand. Make sure it is SEO optimized."}]
    )
    generated_section = completion.choices[0].message.content
    return generated_section  