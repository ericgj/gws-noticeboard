from datetime import datetime

from util.decode import decoded_base64
from model.article import Article
import env

DB = env.db()

@decoded_base64(Article.from_json)
def write(article, ctx):
    id = DB.write_article(article, timestamp=datetime.utcnow())
    return id


