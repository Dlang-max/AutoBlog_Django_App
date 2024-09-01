import requests
from .errors import BlogUploadError, ImageUploadError, ChangeFeaturedImageError, DeletingBlogError

# HELPER METHODS FOR INTERACTING WITH WORDPRESS REST API #
# ============================================================================== #
def test_member_website_credentials(member_wordpress_post_url='', header=''):
    try:
        response = requests.get(member_wordpress_post_url, headers=header, timeout=10)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.HTTPError:
        return False
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.RequestException:
        return False

    
def post_blog_to_wordpress(member_wordpress_post_url='', header='', blog=None):
    blog_content = blog.content

    try:
        # Post Blog Content to WordPress
        post = {
            "title" : blog.title,
            "content" : blog_content,
            "status" : "publish",
        }
        post_response = requests.post(member_wordpress_post_url, headers=header, json=post)
        post_id = post_response.json().get("id")
    except requests.exceptions.ConnectionError:
        raise BlogUploadError("Error uploading blog to WordPress")
    return post_id

def post_image_to_wordpress(member_wordpress_media_url='', header='', blog=None):
    try:
        media = {
            'file': ('header_image.webp', blog.image, 'image/webp'),
            'status': 'publish'
        }
        media_response = requests.post(member_wordpress_media_url, headers=header, files=media)
        media_id = media_response.json().get('id')
    except requests.exceptions.ConnectionError:
        raise ImageUploadError("Error uploading image to WordPress")
    return media_id

def update_blogs_featured_image(member_wordpress_current_post_url='', header='', media_id=''):
    try:
        featured_payload = {
            'featured_media': media_id
        }
        # Update Blog's featured image
        requests.post(member_wordpress_current_post_url, headers=header, json=featured_payload)
    except requests.exceptions.ConnectionError:
        raise ChangeFeaturedImageError("Error changing blog's featured image")

def delete_blog_from_wordpress(member_wordpress_post_url='', header='', post_id=''):
    current_url = member_wordpress_post_url + f"/{post_id}"
    try:
        requests.delete(current_url, headers=header)
    except requests.exceptions.ConnectionError:
        raise DeletingBlogError("Error deleting blog")

# HELPER METHODS FOR HTML STYLING #
# ============================================================================== # 
def format_blog(blog):
    content = ""
    for i in range(1, 6):
        subheading = getattr(blog, f"subheading_{i}")
        section = getattr(blog, f"section_{i}")
        content += format_subheading_and_section(format_subheading(subheading), format_section(section))

    return f"<article style=\"font-family: Arial; display: flex; flex-direction: column; align-items: center;\">{content}</article>"

def format_title(title):
    title_html = f"<h2>{title}</h2>"
    return title_html

def format_subheading(subheading):
    subheading_html = f"<h2>{subheading}</h2>"    
    return subheading_html

def format_section(section):
    section_html = f"<p> &emsp; {section}</p>"
    return section_html

def format_subheading_and_section(subheading, section):
    subheading_and_section_html = f"<section style=\"display: flex; flex-direction: column; align-items: center;\">{subheading} {section}</section> "
    return subheading_and_section_html