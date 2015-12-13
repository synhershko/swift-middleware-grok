from swift.common.swob import Request, Response
from swift.common.utils import register_swift_info, split_path, get_logger
from swift.common.http import HTTP_BAD_REQUEST

try:
    import simplejson as json
except ImportError:
    import json

from grok import name, version

import StringIO
import pygrok

class GrokMiddleware(object):

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='grok')

    def __call__(self, env, start_response):
        req = Request(env)
        resp = req.get_response(self.app)

        try:
            (version, account, container, objname) = split_path(req.path_info, 1, 4, True)
        except ValueError:
            return resp(env, start_response)

        is_grok_request = req.params.has_key('grok') or 'grok-pattern' in req.headers

        # grok request has to be explicit, and only expected for GET operations
        if not req.method == 'GET' or not is_grok_request:
            return resp(env, start_response)

        self.logger.debug('Calling grok middleware')

        # make sure we have an object to work on
        if not objname or not resp.status_int == 200:
            return resp(env, start_response)

        # the grok pattern is expected to be in the request headers
        # if the pattern is missing, we ignore the grok request
        pattern = req.headers.get('grok-pattern')
        if not pattern:
            self.logger.debug('Object found, but no pattern requested, aborting')
            return self.get_err_response('Grok pattern is missing')(env, start_response)

        self.logger.debug('Starting grok operation')

        # we are going to assume the retrieved object is string object
        # and iterate through lines of resp.body and execute grok_match
        grokked_content = ''
        try:
            strbuf = StringIO.StringIO(resp.body)
            for line in strbuf:
                parsed_line = pygrok.grok_match(line, pattern)
                grokked_content += json.dumps(parsed_line) + '\n'
        except Exception as e:
            return self.get_err_response(str(e))(env, start_response)

        resp.body = grokked_content

        return resp(env, start_response)

    def get_err_response(self, msg='Unable to process requested file'):
        self.logger.error(msg)
        resp = Response(content_type='text/xml')
        resp.status = HTTP_BAD_REQUEST
        resp.body = '<?xml version="1.0" encoding="UTF-8"?>\r\n<Error>\r\n  ' \
                        '<Code>%s</Code>\r\n  <Message>%s</Message>\r\n</Error>\r\n' \
                        % (HTTP_BAD_REQUEST, msg)
        return resp


def filter_factory(global_conf, **local_conf):
    """
    Executed once when the proxy is started.
    @global_conf dictionary containing the config values located
    in the default section of the proxy-server.conf.
    @local_conf dictionary containing the config values located
    in this middleware's config section.
    @returns ...
    """

    conf = global_conf.copy()
    conf.update(local_conf)

    # Make the middleware discoverable by clients
    # Clients can then make a GET request to http://127.0.0.1:8080/info
    register_swift_info(name)

    def grok_filter(app):
        """
        @app the next middleware in the pipeline.
        """
        return GrokMiddleware(app, conf)

    return grok_filter
