# This file is part of beets.
# Copyright 2015, Fabrice Laporte
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Abstraction layer to resize images using PIL, ImageMagick, or a
public resizing proxy if neither is available.
"""
from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import urllib
import subprocess
import os
import re
from tempfile import NamedTemporaryFile

from beets import logging
from beets import util

# Resizing methods
PIL = 1
IMAGEMAGICK = 2
WEBPROXY = 3

PROXY_URL = 'http://images.weserv.nl/'

log = logging.getLogger('beets')


def resize_url(url, maxwidth):
    """Return a proxied image URL that resizes the original image to
    maxwidth (preserving aspect ratio).
    """
    return '{0}?{1}'.format(PROXY_URL, urllib.urlencode({
        'url': url.replace('http://', ''),
        'w': bytes(maxwidth),
    }))


def temp_file_for(path):
    """Return an unused filename with the same extension as the
    specified path.
    """
    ext = os.path.splitext(path)[1]
    with NamedTemporaryFile(suffix=ext, delete=False) as f:
        return f.name


def pil_resize(maxwidth, path_in, path_out=None):
    """Resize using Python Imaging Library (PIL).  Return the output path
    of resized image.
    """
    path_out = path_out or temp_file_for(path_in)
    from PIL import Image
    log.debug(u'artresizer: PIL resizing {0} to {1}',
              util.displayable_path(path_in), util.displayable_path(path_out))

    try:
        im = Image.open(util.syspath(path_in))
        size = maxwidth, maxwidth
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(path_out)
        return path_out
    except IOError:
        log.error(u"PIL cannot create thumbnail for '{0}'",
                  util.displayable_path(path_in))
        return path_in


def im_resize(maxwidth, path_in, path_out=None):
    """Resize using ImageMagick's ``convert`` tool.
    Return the output path of resized image.
    """
    path_out = path_out or temp_file_for(path_in)
    log.debug(u'artresizer: ImageMagick resizing {0} to {1}',
              util.displayable_path(path_in), util.displayable_path(path_out))

    # "-resize widthxheight>" shrinks images with dimension(s) larger
    # than the corresponding width and/or height dimension(s). The >
    # "only shrink" flag is prefixed by ^ escape char for Windows
    # compatibility.
    try:
        util.command_output([
            'convert', util.syspath(path_in),
            '-resize', '{0}x^>'.format(maxwidth), path_out
        ])
    except subprocess.CalledProcessError:
        log.warn(u'artresizer: IM convert failed for {0}',
                 util.displayable_path(path_in))
        return path_in
    return path_out


BACKEND_FUNCS = {
    PIL: pil_resize,
    IMAGEMAGICK: im_resize,
}


class Shareable(type):
    """A pseudo-singleton metaclass that allows both shared and
    non-shared instances. The ``MyClass.shared`` property holds a
    lazily-created shared instance of ``MyClass`` while calling
    ``MyClass()`` to construct a new object works as usual.
    """
    def __init__(cls, name, bases, dict):
        super(Shareable, cls).__init__(name, bases, dict)
        cls._instance = None

    @property
    def shared(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class ArtResizer(object):
    """A singleton class that performs image resizes.
    """
    __metaclass__ = Shareable

    def __init__(self, method=None):
        """Create a resizer object for the given method or, if none is
        specified, with an inferred method.
        """
        self.method = self._check_method(method)
        log.debug(u"artresizer: method is {0}", self.method)
        self.can_compare = self._can_compare()

    def resize(self, maxwidth, path_in, path_out=None):
        """Manipulate an image file according to the method, returning a
        new path. For PIL or IMAGEMAGIC methods, resizes the image to a
        temporary file. For WEBPROXY, returns `path_in` unmodified.
        """
        if self.local:
            func = BACKEND_FUNCS[self.method[0]]
            return func(maxwidth, path_in, path_out)
        else:
            return path_in

    def proxy_url(self, maxwidth, url):
        """Modifies an image URL according the method, returning a new
        URL. For WEBPROXY, a URL on the proxy server is returned.
        Otherwise, the URL is returned unmodified.
        """
        if self.local:
            return url
        else:
            return resize_url(url, maxwidth)

    @property
    def local(self):
        """A boolean indicating whether the resizing method is performed
        locally (i.e., PIL or ImageMagick).
        """
        return self.method[0] in BACKEND_FUNCS

    def _can_compare(self):
        """A boolean indicating whether image comparison is available"""

        return self.method[0] == IMAGEMAGICK and self.method[1] > (6, 8, 7)

    @staticmethod
    def _check_method(method=None):
        """A tuple indicating whether current method is available and its
        version. If no method is given, it returns a supported one.
        """
        # Guess available method
        if not method:
            for m in [IMAGEMAGICK, PIL]:
                _, version = ArtResizer._check_method(m)
                if version:
                    return (m, version)
            return (WEBPROXY, (0))

        if method == IMAGEMAGICK:

            # Try invoking ImageMagick's "convert".
            try:
                out = util.command_output(['identify', '--version'])

                if 'imagemagick' in out.lower():
                    pattern = r".+ (\d+)\.(\d+)\.(\d+).*"
                    match = re.search(pattern, out)
                    if match:
                        return (IMAGEMAGICK,
                                (int(match.group(1)),
                                 int(match.group(2)),
                                 int(match.group(3))))
                    return (IMAGEMAGICK, (0))

            except (subprocess.CalledProcessError, OSError):
                return (IMAGEMAGICK, None)

        if method == PIL:
            # Try importing PIL.
            try:
                __import__('PIL', fromlist=['Image'])
                return (PIL, (0))
            except ImportError:
                return (PIL, None)
