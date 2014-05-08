import requests

class NestException(Exception):
    def __init__(self, error, value):
        self.error = error
        self.value = value

    def __unicode__(self):
        return "{0} (Error: {1})".format(self.value, self.error)

    def __str__(self):
        return self.__unicode__()

class NestHttpError(NestException):
    pass

class NestInvalidResponse(NestHttpError):
    pass

class NestUnauthorized(NestException):
    pass



class Nest(object):
    def __init__(self, username, password, token=None, user_id=None, user=None, url="https://home.nest.com", data=None):
        self.username = username
        self.password = password
        self.is_authenticated = False
        self.token = token
        self.user_id = user_id
        self.user = user
        self.url = url
        self.data = data

        if token is None:
            self.login()
            self.get_status()

    def send_request(self, endpoint, payload=None, headers={}):
        headers['user-agent'] = "Nest/1.1.0.10 CFNetwork/548.0.4"
        headers["X-nl-protocol-version"] = "1"

        if self.is_authenticated:
            headers["Authorization"] = "Basic {0}".format(self.token)
            headers["X-nl-user-id"] = self.user_id

        try:
            url = "{0}{1}".format(self.url, endpoint)

            if payload is not None:
                response = requests.post(url, data=payload, headers=headers)
            else:
                response = requests.get(url, data=payload, headers=headers)

            if response.status_code != 200:
                raise NestHttpError("HTTP Error", "There was a problem sending the reqest to NEST")

            return response.json()
        except:
            raise NestHttpError("HTTP Error", "There was a problem sending the reqest to NEST")


    def login(self):
        payload = {
            'username': self.username,
            'password': self.password
        }
        response = self.send_request('/user/login', payload=payload)
        self.token = response.get('access_token')
        self.user_id = response.get('userid')
        self.user = response.get('user')
        self.url = response.get('urls', {}).get('transport_url', self.url)
        self.is_authenticated = True

    def get_status(self):
        response = self.send_request('/v3/mobile/{0}'.format(self.user))
        self.data = response

    def _convertFahrenheitToCelsius(self,temp):
        return float(temp - 32) * float(5.0 / 9.0)

    def _convertCelsiusToFahrenheit(self,temp):
        return float(temp) * float(9.0 /5.0 ) + 32

    def get_weather(self, postal_code=None):
        raise NotImplementedError()

    def get_user_locations(self):
        raise NotImplementedError()

    def get_device_schedule(self, serial_nnumber=None):
        raise NotImplementedError()

    def get_next_scheduled_event(self, serial_nnumber=None):
        raise NotImplementedError()

    def get_device_info(self, serial_nnumber=None):
        raise NotImplementedError()

    def get_energy_latest(self, serial_number=None):
        raise NotImplementedError()

    def turn_off(self, serial_number=None):
        raise NotImplementedError()

    def set_away(self, serial_number=None):
        raise NotImplementedError()
