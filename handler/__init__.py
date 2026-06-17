from handler.base import BaseHandler
from handler.get_routes import GetRoutesMixin
from handler.post_routes import PostRoutesMixin


class Handler(GetRoutesMixin, PostRoutesMixin, BaseHandler):
    pass
