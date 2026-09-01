import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.bazaario import create_app


class VercelRewritePath:
    """Restore the public API path after Vercel's internal function rewrite."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO", "").rstrip("/") in {
            "/api/index",
            "/api/index.py",
        }:
            route_path = None
            forwarded_query = []
            for key, value in parse_qsl(
                environ.get("QUERY_STRING", ""), keep_blank_values=True
            ):
                if key == "path" and route_path is None:
                    route_path = value
                else:
                    forwarded_query.append((key, value))
            if route_path is not None:
                environ["PATH_INFO"] = f"/api/{route_path.lstrip('/')}"
                environ["QUERY_STRING"] = urlencode(forwarded_query, doseq=True)
        return self.wsgi_app(environ, start_response)


app = VercelRewritePath(create_app())
