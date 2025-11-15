"""Custom middleware for the resume manager app"""

from django.conf import settings


class ConditionalXFrameOptionsMiddleware:
    """
    Custom middleware to handle X-Frame-Options header.
    Allows SAMEORIGIN by default but can be customized per view.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.x_frame_options = getattr(settings, 'X_FRAME_OPTIONS', 'SAMEORIGIN')
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Don't override if the view already set the header
        if 'X-Frame-Options' not in response:
            response['X-Frame-Options'] = self.x_frame_options
        
        return response
