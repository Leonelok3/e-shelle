class TiboSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/tibo/"):
            response.setdefault("X-TIBO-App", "dropshipping")
            response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

