from hashlib import sha1

from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase
from tornado.test.util import unittest
from PIL import Image

from robohash.webfront import ImgHandler


class BaseImageHandlerTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application(((r"/", ImgHandler), # uses remote_ip
                            (r"/(.+)", ImgHandler),))

    def get_response(self, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        response.rethrow()
        return response


class BasicFunctionalityTest(BaseImageHandlerTest):

    def test_basic_get(self):
        response = self.get_response("/foo")
        self.assertEqual(response.code, 200)

        type = response.headers.get('content-type')
        self.assertEqual(type, 'image/png')

class ArgumentParserTest(BaseImageHandlerTest):

    def test_size_args(self):
        response = self.get_response("/foo?size=222x222")
        self.assertEqual(response.code, 200)

        type = response.headers.get('content-type')
        self.assertEqual(type, 'image/png')

        im = Image.open(response.buffer)
        self.assertEqual(im.size, (222, 222))


    def test_directory_style_args(self):
        response = self.get_response("/foo/size_222x222")
        self.assertEqual(response.code, 200)

        im = Image.open(response.buffer)
        self.assertEqual(im.size, (222, 222))


class ImageHandlerIPAddrMode(BaseImageHandlerTest):

    def test_empty_get_is_ip_get(self):
        r1 = self.get_response("/")
        self.assertEqual(r1.code, 200)
        r2 = self.get_response("/127.0.0.1")
        self.assertEqual(r2.code, 200)
        r1_hsh = sha1(r1.body).hexdigest()
        r2_hsh = sha1(r2.body).hexdigest()
        self.assertEqual(r1_hsh, r2_hsh)


if __name__ == "__main__":
    unittest.main()
