#!/usr/bin/env python3.3

import os
import struct
import hashlib
import ssl
import hmac
import math
import itertools
import re
import logging

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.log
import tornado.options

from PIL import Image


SETS_DIR = os.path.join(os.path.dirname(__file__), 'sets')
PUBLIC_SEED = b''


def simple_prng(input: 'str or bytes', seed:'str or bytes'=PUBLIC_SEED):
    """Simple deterministic random number generator for expanding seed. Not for general purpose use.
        Yields 64 bit unsigned integers. Seed is optional and can help against chosen input attacks."""
    input, seed = [s.encode('utf-8') if isinstance(s, str) else s for s in (input, seed)]
    pool = hmac.new(seed, input, hashlib.sha512).digest()
    for i in itertools.count():
        for value in struct.unpack("<QQQQQQQQ", pool):
            yield value
        pool = hmac.new(seed, pool, hashlib.sha512).digest()


class RoboPartsSet(object):
    """This is one full set of robot image components.
       It will pick image files given a sequence of input numbers."""

    def __init__(self, name, sets_dir=SETS_DIR):
        self.set_dir = os.path.join(sets_dir, name)
        self.choices = []
        self.choice_bits = 0

        for root, dirs, files in os.walk(self.set_dir, topdown=False):
            imgs = [f for f in files if f[-4:] == ".png"]
            if len(imgs) > 0:
                choice_group = os.path.relpath(root, start=self.set_dir)
                self.choices.append((choice_group, imgs))
                self.choice_bits += math.log(len(imgs), 2)
        if self.choice_bits < 12:
            raise Exception("Insufficent robot parts for set. %s has %0.1f bits" % (name, self.choice_bits))

    def pick_files(self, prng: "iterable of random integers"):
        """Returns image file choices and tag (caching) function for the robo-hash."""
        files = []
        indexes = []
        for (group, options), rnd in zip(self.choices, prng):
            idx = rnd % len(options)
            files.append(os.path.join(self.set_dir, group, options[idx]))
            indexes.append(idx)
        return files, lambda: ",".join([str(i) for i in indexes])


class RoboPartsSetWithColors(object):
    """Similar interface to RobotParts, but has multiple color options."""

    def __init__(self, name, sets_dir=SETS_DIR):
        self.name = name
        colors_dir = os.path.join(sets_dir, name)
        self.colors = [d for d in os.listdir(colors_dir) if os.path.isdir(os.path.join(colors_dir, d))]
        self.sets = [RoboPartsSet(os.path.join(name, c), sets_dir=sets_dir) for c in self.colors]
        if len(self.sets) < 2:
            raise Exception("Expected multiple color-sets; didn't find them.")

    def pick_files(self, prng):
        """Returns image file choices and tag (caching) function for the robo-hash."""
        idx = prng.__next__() % len(self.sets)
        color_set = self.sets[idx]
        robo_choice, tag_key = color_set.pick_files(prng)
        return robo_choice, lambda: "%s,%s" % (idx, tag_key())


class RobotHashBuilder(object):
    def __init__(self):
        self.sets = {
            'set1': RoboPartsSetWithColors('set1'),
            'set2': RoboPartsSet('set2'),
            'set3': RoboPartsSet('set3'),
        }

    def build_image(self, input, seed=PUBLIC_SEED, set_name='set1'):
        """Builds and returns a robohash image from a given input seed.

            input - data to build the image from.
            seed - can be used for an hmac secret in parts picking process.
            set_name (set1|set2|set3)

            this builds the image in the native size of the set.
        """
        if set_name not in self.sets:
            raise Exception("Bad set name: %s" % set_name)
        robo_set = self.sets[set_name]

        prng = simple_prng(input, seed=seed)
        files, tag_key = robo_set.pick_files(prng)
        files.sort(key=lambda x: x.split("#")[1])

        # build hash of decision tree:
        #htag_input = "%s:%s" % (set_name, tag_key())
        #htag = hashlib.sha256(htag_input.encode('utf-8')).hexdigest()

        robo_img = Image.open(files[0])
        for f in files[1:]:
            img = Image.open(f)
            robo_img.paste(img, (0, 0), img)
        return robo_img


class RawHashHandler(tornado.web.RequestHandler):
    """Location handler for RoboHash"""

    def initialize(self, robot_builder=None, rnd=False, default_size=(200, 200)):
        self.robot_builder = robot_builder
        self.rnd = rnd
        self.default_size = default_size

    def get(self, argument=None, size=(200, 200)):
        if self.rnd and not argument:
            argument = ssl.RAND_bytes(8) # 64 bits of entropy

        set = self.get_argument('set', 'set1')
        if set == '':
            set = 'set1'
        elif set not in ('set1', 'set2', 'set3'):
            return self.send_error(400)

        build_args = {
            'seed': self.get_argument('seed', PUBLIC_SEED),
            'set_name': set,
        }

        im = self.robot_builder.build_image(argument, **build_args)
        im = im.resize(self.pick_size(), Image.ANTIALIAS)

        self.set_header("Content-Type", "image/png")
        im.save(self, format='png')

    def pick_size(self):
        size_arg = re.match("^(?P<x>\d\d\d?)x(?P<y>\d\d\d?)$", self.get_argument('size', ''))
        if size_arg:
            return (int(size_arg.group('x')), int(size_arg.group('y')))
        else:
            return self.default_size


if __name__ == "__main__":
    tornado.log.enable_pretty_logging()

    robot_builder = RobotHashBuilder()
    application = tornado.web.Application([
        (r"/bot/(.*)", RawHashHandler, {'robot_builder': robot_builder}),
        (r"/rnd", RawHashHandler, {'robot_builder': robot_builder, 'rnd': True}),
    ])
    application.listen(8888)
    logging.info("Starting server.")
    tornado.ioloop.IOLoop.instance().start()

