#!/usr/bin/env python
#
from actingweb import actor
from actingweb import oauth
from actingweb import config
from spark import ciscospark

import logging

import os
from google.appengine.ext.webapp import template

__all__ = [
    'on_www_paths',
]


def on_www_paths(myself, req, auth, path=''):
    if path == '' or not myself:
        logging.info('Got an on_www_paths without proper parameters.')
        return False
    spark = ciscospark.ciscospark(auth, myself.id)
    if path == 'getattachment':
        template_values = {
            'url': str(req.request.get('url')),
            'filename': str(req.request.get('filename')),
        }
        template_path = os.path.join(os.path.dirname(__file__), '../templates/spark-getattachment.html')
        req.response.write(template.render(template_path, template_values).encode('utf-8'))
    return False
