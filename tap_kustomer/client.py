from datetime import datetime
from time import sleep
import backoff
import requests
from singer import metrics, utils
import singer

API_VERSION = 'v1'
LOGGER = singer.get_logger()
RATE_LIMIT_REMAINING = 'x-ratelimit-remaining'
RATE_LIMIT_RESET = 'x-ratelimit-reset'


class Server5xxError(Exception):
    pass


class Server429Error(Exception):
    pass


class KustomerError(Exception):
    pass


class KustomerBadRequestError(KustomerError):
    pass


class KustomerUnauthorizedError(KustomerError):
    pass


class KustomerPaymentRequiredError(KustomerError):
    pass


class KustomerNotFoundError(KustomerError):
    pass


class KustomerConflictError(KustomerError):
    pass


class KustomerForbiddenError(KustomerError):
    pass


class KustomerInternalServiceError(KustomerError):
    pass


ERROR_CODE_EXCEPTION_MAPPING = {
    400: KustomerBadRequestError,
    401: KustomerUnauthorizedError,
    402: KustomerPaymentRequiredError,
    403: KustomerForbiddenError,
    404: KustomerNotFoundError,
    409: KustomerForbiddenError,
    500: KustomerInternalServiceError
}


def get_exception_for_error_code(error_code):
    return ERROR_CODE_EXCEPTION_MAPPING.get(error_code, KustomerError)


def raise_for_error(response):
    try:
        response.raise_for_status()
    except (requests.HTTPError, requests.ConnectionError) as error:
        try:
            content_length = len(response.content)
            if content_length == 0:
                # There is nothing we can do here since Kustomer has neither sent
                # us a 2xx response nor a response content.
                return
            response = response.json()
            if ('error' in response) or ('errorCode' in response):
                message = '%s: %s' % (response.get('error', str(error)),
                                      response.get('message', 'Unknown Error'))
                error_code = response.get('error', {}).get('code')
                ex = get_exception_for_error_code(error_code)
                if response.status_code == 401 and 'Expired token' in message:
                    LOGGER.error(
                        "Your API token has expired as per Kustomer’s security \
                        policy. \n Please re-authenticate your connection to generate a new token \
                        and resume extraction.")
                    raise ex(message)
                raise KustomerError(error)
        except (ValueError, TypeError):
            raise KustomerError(error)


class KustomerClient():
    def __init__(self, token, user_agent=None):
        self.__token = token
        self.__user_agent = user_agent
        self.__session = requests.Session()
        self.__verified = False
        self.base_url = 'https://api.kustomerapp.com/{}'.format(API_VERSION)

    def __enter__(self):
        self.__verified = self.check_token()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.__session.close()

    @backoff.on_exception(backoff.expo, Server5xxError, max_tries=5, factor=2)
    @utils.ratelimit(250, 60)
    def check_token(self):
        if self.__token is None:
            raise Exception('Error: Missing access_token.')
        headers = {}
        if self.__user_agent:
            headers['User-Agent'] = self.__user_agent
        headers['Authorization'] = 'Bearer {}'.format(self.__token)
        headers['Accept'] = 'application/json'
        response = self.__session.get(
            # Simple endpoint that returns 1 Account record (to check API/token access):
            url='{}/{}/'.format(self.base_url, 'users/current'),
            headers=headers)
        if response.status_code != 200:
            LOGGER.error('Error status_code = %s', response.status_code)
            raise_for_error(response)
        else:
            resp = response.json()
            if 'results' in resp:
                return True
        return False

    @backoff.on_exception(backoff.expo,
                          (Server5xxError, ConnectionError, Server429Error),
                          max_tries=5,
                          factor=2)
    @utils.ratelimit(250, 60)
    def request(self, method, path=None, url=None, data=None, **kwargs):
        if not self.__verified:
            self.__verified = self.check_token()

        if not url and path:
            url = '{}/{}/'.format(self.base_url, path)

        if 'endpoint' in kwargs:
            endpoint = kwargs['endpoint']
            del kwargs['endpoint']
        else:
            endpoint = None

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Authorization'] = 'Bearer {}'.format(self.__token)
        kwargs['headers']['Accept'] = 'application/json'

        if self.__user_agent:
            kwargs['headers']['User-Agent'] = self.__user_agent

        if method == 'POST':
            kwargs['headers']['Content-Type'] = 'application/json'

        with metrics.http_request_timer(endpoint) as timer:
            response = self.__session.request(method, url, data=data, **kwargs)
            timer.tags[metrics.Tag.http_status_code] = response.status_code

        if response.status_code >= 500:
            raise Server5xxError()

        # Kustomer API rate limiting. If rate limit exceeded wait until limit reset.
        # See, https://dev.kustomer.com/v1/welcome/rate-limiting
        # x-ratelimit-reset is the header returned when the rate limit has
        # been exceeded, and represents the time (UTC epoch seconds) when
        # the rate limit window will reset.
        if RATE_LIMIT_REMAINING in response.headers and int(
                response.headers[RATE_LIMIT_REMAINING]) <= 0:
            if RATE_LIMIT_RESET in response.headers:
                reset_in = response.headers[RATE_LIMIT_RESET]
                now = datetime.now().timestamp()
                retry_in = reset_in - now
                LOGGER.info("Rate limit exceeded, retrying in %s: ", retry_in)
                sleep(retry_in)
                raise Server429Error()

        if response.status_code != 200:
            raise_for_error(response)

        return response.json()

    def get(self, url, path, **kwargs):
        return self.request('GET', url=url, path=path, **kwargs)

    def post(self, url, path, data, **kwargs):
        return self.request('POST', url=url, path=path, data=data, **kwargs)

    def fetch(self, method, url, path, data=None, **kwargs):
        if method == 'POST':
            return self.post(url=url, path=path, data=data, **kwargs)
        return self.get(url=url, path=path, **kwargs)
