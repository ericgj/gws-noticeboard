from util.decode import decoded_base64
from model.article import Request, Article

import env


@decoded_base64(Request.from_json)
def fetch(req, ctx):
    env.publish(fetch_value(req).to_json())
    return ""


def fetch_value(req):
    return Article.fetch(req)
