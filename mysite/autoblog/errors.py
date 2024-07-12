class BlogGenerationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class BlogUploadError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class ImageUploadError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class ChangeFeaturedImageError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class DeletingBlogError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message