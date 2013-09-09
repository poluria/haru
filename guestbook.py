import os
import urllib

from google.appengine.api import users

from google.appengine.ext import ndb

import jinja2
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)+'/view'), extensions=['jinja2.ext.autoescape'])
DEFAULT_GUESTBOOK_NAME = 'default_guestbook'


# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)


class Greeting(ndb.Model):
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)


class HomeHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('home.html')
        self.response.write(template.render())


class PostHandler(webapp2.RequestHandler):
    def get(self):
        guestbook_name = self.request.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)

        greetings_query = Greeting.query(ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
        greetings = greetings_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'greetings': greetings,
            'guestbook_name': urllib.quote_plus(guestbook_name),
            'url': url,
            'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('posts.html')
        self.response.write(template.render(template_values))


class PostCreateHandler(webapp2.RequestHandler):
    def get(self):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))

        image_url = self.request.get('image_url')

        template_values = {
            'image_url': image_url,
        }

        template = JINJA_ENVIRONMENT.get_template('post_form.html')
        self.response.write(template.render(template_values))

    def post(self):
        guestbook_name = self.request.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)
        greeting = Greeting(parent=guestbook_key(guestbook_name))

        if users.get_current_user():
            greeting.author = users.get_current_user()

        greeting.content = self.request.get('content')
        greeting.put()

        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/posts')

class ImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/images/upload')

        template_values = {
            'upload_url': upload_url,
        }

        template = JINJA_ENVIRONMENT.get_template('image_upload.html')
        self.response.write(template.render(template_values))

    def post(self):
        upload_files = self.get_uploads('image')
        blob_info = upload_files[0]
        image_url = '/images/%s' % blob_info.key()
        self.redirect('/posts/create?image_url=%s' % image_url)

class ImageHandler(webapp2.RequestHandler):
    def get(self, blob_key):
        blob_key = str(urllib.unquote(blob_key))
        img = images.Image(blob_key=blob_key)
        img.resize(width=80, height=100)
        thumbnail = img.execute_transforms(output_encoding=images.JPEG)

        self.response.headers['Content-Type'] = 'image/jpeg'
        self.response.out.write(thumbnail)

application = webapp2.WSGIApplication([
    ('/', HomeHandler),
    ('/posts', PostHandler),
    ('/posts/create', PostCreateHandler),
    ('/images/upload', ImageUploadHandler),
    ('/images/(.+)', ImageHandler),
], debug=True)

