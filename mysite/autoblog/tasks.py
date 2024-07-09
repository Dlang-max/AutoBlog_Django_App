import openai
from celery import app
from openai import OpenAI
from celery import shared_task
from .models import User, Member, Blog

client = OpenAI()

@shared_task
def write_blog(username=None, title='', addition_info=''):
    user = User.objects.get(username=username)
    member = Member.objects.get(user=user)
    blog = Blog.objects.get(author=member)
    outline = writeBlogOutline(title=title)

    # BUILD BLOG
    try:


        meta_keywords = writeMetaKeywords(outline=outline)
        meta_description = writeMetaDescription(outline=outline)

        blog.title = title
        blog.meta_keywords = meta_keywords
        blog.meta_description = meta_description

        sections = ["first", "second", "third", "fourth", "concluding"]

        for i, section in enumerate(sections, start=1):
            subheading = writeHeading(section=section, outline=outline)
            section = writeSection(section=section, outline=outline)

            setattr(blog, f"subheading_{i}", subheading)
            setattr(blog, f"section_{i}", section) 

        blog.save()

    except openai.APIError as e:
        member.blogs_remaining += 1
        member.save()
        print("openai.APIError encountered when trying to generate blog for ", username, flush=True)
    return True

# STILL NEED TO TEST IMAGE GENERATION
# VERY EXPENSIVE TO GENERATE IMAGES
def generateBlogImage(title=''):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"{title}",
        size="1024x1024",
        quality="standard",
    )

    image_url = response.data[0].url
    return image_url



def writeBlogOutline(title=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog outlines for a living. You have a friendly tone of voice. You have a conversational writting style. Create a long form content outline in english for the blog post titled {title}. The content outline should include a minumum of 5 subheadings and headings. The outline should be extensive and hsould conver the entire topic. Create detailed subheadings that are engaging and chatchy. Do not write the blog post. Please only write the outline of the blog post. Please do not number the headings. Please add newline space between headings and subheadings. Do not self reference. Do not explain what you are doing"}]
    )
    outline = completion.choices[0].message.content
    return outline

def writeHeading(section='', outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog outlines for a living. You have a friendly tone of voice. You have a conversational writting style. Using this blog outline: {outline}, write the {section} subheading for this blog. Make sure this subheading is SEO optimized."}]
    )
    outline = completion.choices[0].message.content
    return outline

def writeSection(section='', subheading='', outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog outlines for a living. You have a friendly tone of voice. You have a conversational writting style. Using this blog outline: {outline} and the subheading {subheading}, write the {section} content section for this blog. Do NOT include the name of this subheading in this section. Keep this section between 150 and 200 words. Also use language that an 8th grader can understand. Make sure it is SEO optimized."}]
    )
    outline = completion.choices[0].message.content
    return outline

def writeMetaKeywords(outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog meta keywords for a living. Here is the outline for the blog {outline}. Just return 3 specific meta keywords related to this blog. Make sure they aren't too long. You NEED to keep it to 90 characters. Make sure they are SEO optimized."}]
    )
    keywords = completion.choices[0].message.content
    return keywords

def writeMetaDescription(outline=''):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'user', "content": f"Please ignore all previous instructions. You are an expert copywriter who creates blog meta descriptions for a living. Here is the outline for the blog {outline}. Just return a meta description for this blog. You NEED to keep it to 150 characters. Make sure it is SEO optimized."}]
    )
    description = completion.choices[0].message.content
    return description    