from .models import User, Member, Blog
from celery import app
from celery import shared_task
import openai
from openai import OpenAI

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

        subheading_1 = writeHeading(section='first', outline=outline)
        section_1 = writeSection(section='first', subheading=subheading_1, outline=outline)

        subheading_2 = writeHeading(section='second', outline=outline)
        section_2 = writeSection(section='second', subheading=subheading_2, outline=outline)

        subheading_3 = writeHeading(section='third', outline=outline)
        section_3 = writeSection(section='third', subheading=subheading_3, outline=outline)

        subheading_4 = writeHeading(section='fourth', outline=outline)
        section_4 = writeSection(section='fourth', subheading=subheading_4, outline=outline)

        subheading_5 = writeHeading(section='concluding', outline=outline)
        section_5 = writeSection(section='concluding', subheading=subheading_5, outline=outline)
        

        blog.meta_keywords = meta_keywords
        blog.meta_description = meta_description
        
        blog.title = title
        blog.subheading_1, blog.section_1 = subheading_1, section_1 
        blog.subheading_2, blog.section_2 = subheading_2, section_2 
        blog.subheading_3, blog.section_3 = subheading_3, section_3 
        blog.subheading_4, blog.section_4 = subheading_4, section_4 
        blog.subheading_5, blog.section_5 = subheading_5, section_5 
        blog.save()

    except openai.APIError as e:
        member.blogs_remaining += 1
        member.save()
        print("openai.APIError encountered when trying to generate blog for ", username, flush=True)
    return True

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