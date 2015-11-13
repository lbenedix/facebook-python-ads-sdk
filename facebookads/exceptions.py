# Copyright 2014 Facebook, Inc.

# You are hereby granted a non-exclusive, worldwide, royalty-free license to
# use, copy, modify, and distribute this software in source code or binary
# form for use in connection with the web services and APIs provided by
# Facebook.

# As with any software that integrates with the Facebook platform, your use
# of this software is subject to the Facebook Developer Principles and
# Policies [http://developers.facebook.com/policy/]. This copyright notice
# shall be included in all copies or substantial portions of the software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""
The exceptions module contains Exception subclasses whose instances might be
raised by the sdk.
"""

import json
import re


class FacebookError(Exception):
    """
    All errors specific to Facebook api requests and Facebook ads design will be
    subclassed from FacebookError which is subclassed from Exception.
    """
    pass


class FacebookRequestError(FacebookError):
    """
    Raised when an api request fails. Returned by error() method on a
    FacebookResponse object returned through a callback function (relevant
    only for failure callbacks) if not raised at the core api call method.
    """

    def __init__(
        self, message,
        request_context,
        http_status,
        http_headers,
        body
    ):
        self._message = message
        self._request_context = request_context
        self._http_status = http_status
        self._http_headers = http_headers
        try:
            self._body = json.loads(body)
        except (TypeError, ValueError):
            self._body = body

        self._api_error_code = None
        self._api_error_subcode = None
        self._api_error_type = None
        self._api_error_message = None
        self._api_blame_field_specs = None

        if self._body and isinstance(self._body, dict) and 'error' in self._body:
            self._error = self._body['error']
            if 'message' in self._error:
                self._api_error_message = self._error['message']
            if 'code' in self._error:
                self._api_error_code = self._error['code']
            if 'error_subcode' in self._error:
                self._api_error_subcode = self._error['error_subcode']
            if 'type' in self._error:
                self._api_error_type = self._error['type']
            # workaround for malformed error responses:
            error_data = self._error.get('error_data', {})
            if type(error_data) == dict and error_data.get('blame_field_specs'):
                self._api_blame_field_specs = \
                    self._error['error_data']['blame_field_specs']
        else:
            self._error = None

        # We do not want to print the file bytes
        request = self._request_context
        if 'files' in self._request_context:
            request = self._request_context.copy()
            del request['files']

        super(FacebookRequestError, self).__init__(
            "\n\n" +
            "  Message: %s\n" % self._message +
            "  Method:  %s\n" % request.get('method') +
            "  Path:    %s\n" % request.get('path', '/') +
            "  Params:  %s\n" % request.get('params') +
            "\n" +
            "  Status:  %s\n" % self._http_status +
            "  Response:\n    %s" % re.sub(
                r"\n", "\n    ",
                json.dumps(self._body, indent=2)
            ) +
            "\n"
        )

    def request_context(self):
        return self._request_context

    def http_status(self):
        return self._http_status

    def http_headers(self):
        return self._http_headers

    def body(self):
        return self._body

    def api_error_message(self):
        return self._api_error_message

    def api_error_code(self):
        return self._api_error_code

    def api_error_subcode(self):
        return self._api_error_subcode

    def api_error_type(self):
        return self._api_error_type

    def api_blame_field_specs(self):
        return self._api_blame_field_specs

    @property
    def _sentry_data(self):
        # AB-477 Make FacebookRequestErrors easier to tell apart
        tags = {}
        extra = {}

        headers = self.http_headers()
        wanted = ('X-FB-Debug', 'X-FB-Rev', 'X-FB-Trace-ID')
        if headers:
            for name in (n for n in headers if n in wanted):
                extra[name] = headers[name]

        errdata = (
            ('FB-error-type', self.api_error_type()),
            ('FB-error-code', self.api_error_code()),
            ('FB-error-subcode', self.api_error_subcode()),
            ('FB-error-message', self.api_error_message()),
        )
        errtags = {'FB-error-type'}
        for key, value in errdata:
            extra[key] = str(value)
            if key in errtags:
                tags[key] = value

        return dict(tags=tags, extra=extra)

    @classmethod
    def from_exception(cls, e):
        '''
        helper method to instanciate inherited class of FacebookRequestError
        '''
        return cls(
            message=e._message,
            request_context=e._request_context,
            http_status=e._http_status,
            http_headers=e._http_headers,
            body=e._body,
        )



class FacebookBadResponseError(FacebookRequestError):
    """ A Facebook API response is not parseable as a JSON dict.

        It might be an HTML error page instead, and possibly still have a
        status of 200.
    """
    pass


class FacebookRequestSubError(FacebookRequestError):
    """ Base class for more specific facebook reqeust errors """
    ERROR_CODE = None  # general error code of this error
    SUBCODES = ()  # all subcodes this error should be able to fetch

    @classmethod
    def can_catch(cls, exception):
        return (
            exception.api_error_code() == cls.ERROR_CODE and
            exception.api_error_subcode() in cls.SUBCODES
        )


class FacebookAccessTokenInvalid(FacebookRequestSubError):
    """ The Facebook request faile due to an invalid or expired access token. """

    ERROR_CODE = 190  # general error code for token related errors

    SUBCODE_MALFORMED_TOKEN = None
    SUBCODE_PASSWORD_CHANGED = 460   # user changed password, so the token is no longer valid
    SUBCODE_NO_APP_PERMISSION = 458  # user did not grand permission for this app
    SUBCODE_TOKEN_EXPIRED = 463      # user access token expired
    SUBCODE_UNCONFIRMED_USER = 464   # user is not a confirmed user
    SUBCODE_SESSION_INVALID =  461   # invalid session

    SUBCODES = (
        SUBCODE_MALFORMED_TOKEN,
        SUBCODE_PASSWORD_CHANGED,
        SUBCODE_NO_APP_PERMISSION,
        SUBCODE_TOKEN_EXPIRED,
        SUBCODE_UNCONFIRMED_USER,
        SUBCODE_SESSION_INVALID,
    )


class FacebookBadObjectError(FacebookError):
    """Raised when a guarantee about the object validity fails."""
    pass


class FacebookUnavailablePropertyException(FacebookError):
    """Raised when an object's property or method is not available."""
    pass
