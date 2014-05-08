import requests
from datetime import datetime

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


location_map = {
    '00000000-0000-0000-0000-000100000000': 'Entryway',
    '00000000-0000-0000-0000-000100000001': 'Basement',
    '00000000-0000-0000-0000-000100000002': 'Hallway',
    '00000000-0000-0000-0000-000100000003': 'Den',
    '00000000-0000-0000-0000-000100000004': 'Attic',
    '00000000-0000-0000-0000-000100000005': 'Master Bedroom',
    '00000000-0000-0000-0000-000100000006': 'Downstairs',
    '00000000-0000-0000-0000-000100000007': 'Garage',
    '00000000-0000-0000-0000-000100000008': 'Kids Room',
    '00000000-0000-0000-0000-000100000009': 'Garage "Hallway"',
    '00000000-0000-0000-0000-00010000000a': 'Kitchen',
    '00000000-0000-0000-0000-00010000000b': 'Family Room',
    '00000000-0000-0000-0000-00010000000c': 'Living Room',
    '00000000-0000-0000-0000-00010000000d': 'Bedroom',
    '00000000-0000-0000-0000-00010000000e': 'Office',
    '00000000-0000-0000-0000-00010000000f': 'Upstairs',
    '00000000-0000-0000-0000-000100000010': 'Dining Room'
}


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
            url = endpoint
            if endpoint.startswith('/'):
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
        from pprint import pprint
        pprint(response)

    def _convertFahrenheitToCelsius(self, temp):
        return float(temp - 32) * float(5.0 / 9.0)

    def _convertCelsiusToFahrenheit(self, temp):
        return float(temp) * float(9.0 /5.0) + 32

    def temp_in_celsius(self, temperature, serial_number=None):
        serial_number = self.get_default_serial(serial_number)
        temp_scale = self.get_device_temp_scale(serial_number)
        if temp_scale == 'F':
            return (temperature - 32) / 1.8
        return temperature

    def user_temp_scale(self, celsius, serial_number=None):
        serial_number = self.get_default_serial(serial_number)
        temp_scale = self.get_device_temp_scale(serial_number)
        if temp_scale == 'F':
            return (celsius * 1.8) + 32
        return celsius

    def get_device_temp_scale(self, serial_number=None):
        serial_number = self.get_default_serial(serial_number)
        return self.data.get('device').get(serial_number).get('temperature_scale')

    def get_weather(self, postal_code=None):
        if postal_code is None:
            raise NestException('Weather', 'You need to provide a postal code to get the weather')

        response = self.send_request('https://home.nest.com/api/0.1/weather/forecast/{0}'.format(postal_code))

        weather = {}
        weather['outside_temperature'] = self.user_temp_scale(response.get('now', {}).get('current_temperature'))
        weather['outside_humidity'] = response.get('now', {}).get('current_humidity')

        return weather

    def get_user_locations(self):
        self.get_status()
        structures = self.data.get('structure')
        user_structures = []
        for structure_id, structure in structures.iteritems():
            protects = [p.get('serial_number') for p in self.data.get('topaz', []) if p.get('structure_id') == structure_id]

            weather = self.get_weather(structure.get('postal_code'))
            location_data = {}
            location_data['name'] = structure.get('name')
            location_data['address'] = structure.get('street_address')
            location_data['city'] = structure.get('location')
            location_data['postal_code'] = structure.get('postal_code')
            location_data['country'] = structure.get('country_code')
            location_data['outside_temperature'] = weather.get('outside_temperature')
            location_data['outside_humidity'] = weather.get('outside_humidity')
            location_data['away'] = structure.get('away')
            location_data['away_last_changed'] = datetime.fromtimestamp(structure.get('away_timestamp'))
            location_data['thermostats'] = []
            location_data['protects'] = protects

            user_structures.append(location_data)

        return user_structures

    def get_device_schedule(self, serial_number=None):
        raise NotImplementedError()

    def get_next_scheduled_event(self, serial_number=None):
        raise NotImplementedError()

    def get_device_info(self, serial_number=None):
        self.get_status()
        serial_number = self.get_default_serial(serial_number)

        for protect in self.data.get('topaz', []):
            if serial_number == protect.get('serial_number'):
                info = {}
                info['co_status'] = protect.get('co_status')
                info['smoke_status'] = protect.get('smoke_status')
                info['line_power_present'] = protect.get('line_power_present')
                info['battery_level'] = protect.get('battery_level')
                info['battery_health_state'] = protect.get('battery_health_state')
                info['replace_by_date'] = protect.get('replace_by_date_utc_secs')
                info['last_update'] = datetime.fromtimestamp(protect.get('$timestamp') / 1000)
                info['last_manual_test'] = protect.get('$protect->latest_manual_test_start_utc_secs') if protect.get('$protect->latest_manual_test_start_utc_secs') != 0 else None
                info['serial_number'] = protect.get('serial_number')
                info['location'] = protect.get('structure_id')
                info['name'] = protect.get('description') if protect.get('description') is not None else 'Not set'
                info['where'] = location_map.get(protect.get('spoken_where_id'), protect.get('spoken_where_id'))
                info['tests'] = {}
                info['tests']['led'] = protect.get('component_led_test_passed')
                info['tests']['pir'] = protect.get('component_pir_test_passed')
                info['tests']['temp'] = protect.get('component_temp_test_passed')
                info['tests']['smoke'] = protect.get('component_smoke_test_passed')
                info['tests']['heat'] = protect.get('component_heat_test_passed')
                info['tests']['wifi'] = protect.get('component_wifi_test_passed')
                info['tests']['als'] = protect.get('component_als_test_passed')
                info['tests']['co'] = protect.get('component_co_test_passed')
                info['tests']['us'] = protect.get('component_us_test_passed')
                info['tests']['hum'] = protect.get('component_hum_test_passed')
                info['network'] = {}
                info['network']['online'] = protect.get('component_wifi_test_passed')
                info['network']['local_ip'] = protect.get('wifi_ip_address')
                info['network']['mac_address'] = protect.get('wifi_mac_address')

                return info

        structure = self.data.get('link').get(serial_number).get('structure').split('.')[1]
        manual_away = self.data.get('structure').get(structure).get('away')
        mode = self.data.get('device').get(serial_number).get('current_schedule_mode').lower()
        target_mode = self.data.get('shared').get(serial_number).get('target_temperature_type')

        if manual_away or mode == 'away' or self.data.get('shared').get(serial_number).get('auto_away') > 0:
            mode = "{0},away".format(mode)
            target_mode = 'range'
            away_temp_low = self.data.get('device').get(serial_number).get('away_temperature_low')
            away_temp_high = self.data.get('device').get(serial_number).get('away_temperature_high')
            target_temperatures = [self.user_temp_scale(away_temp_low), self.user_temp_scale(away_temp_high)]
        elif mode == 'range':
            target_mode = 'range'
            target_temp_low = self.data.get('shared').get(serial_number).get('target_temperature_low')
            target_temp_high = self.data.get('shared').get(serial_number).get('target_temperature_high')
            target_temperatures = [self.user_temp_scale(target_temp_low), self.user_temp_scale(target_temp_high)]
        else:
            target_temperatures = self.user_temp_scale(self.data.get('shared').get(serial_number).get('target_temperature'))

        info = {}
        info['current_state'] = {}
        info['current_state']['mode'] = mode
        info['current_state']['temperature'] = self.user_temp_scale(self.data.get('shared').get(serial_number).get('current_temperature'))
        info['current_state']['humidity'] = self.data.get('device').get(serial_number).get('current_humidity')
        info['current_state']['ac'] = self.data.get('shared').get(serial_number).get('hvac_ac_state')
        info['current_state']['heat'] = self.data.get('shared').get(serial_number).get('hvac_heater_state')
        info['current_state']['alt_heat'] = self.data.get('shared').get(serial_number).get('hvac_alt_heat_state')
        info['current_state']['fan'] = self.data.get('shared').get(serial_number).get('hvac_fan_state')
        info['current_state']['auto_away'] = self.data.get('shared').get(serial_number).get('auto_away')
        info['current_state']['manual_away'] = manual_away
        info['current_state']['leaf'] = self.data.get('device').get(serial_number).get('leaf')
        info['current_state']['battery_level'] = self.data.get('device').get(serial_number).get('battery_level')
        info['target'] = {}
        info['target']['mode'] = target_mode
        info['target']['temperature'] = target_temperatures
        info['target']['time_to_target'] = self.data.get('device').get(serial_number).get('time_to_target')
        info['serial_number'] = serial_number
        info['scale'] = self.data.get('device').get(serial_number).get('temperature_scale')
        info['location'] = structure
        info['network'] = self.get_device_network_info(serial_number)
        info['name'] = self.data.get('shared').get(serial_number).get('name') if self.data.get('shared').get(serial_number).get('name') is not None else 'Not set'
        info['where'] = location_map.get(self.data.get('device').get(serial_number).get('where_id'))

        if self.data.get('device').get(serial_number).get('has_humidifier'):
            info['current_state']['humidifier'] = self.data.get('device').get(serial_number).get('humidifier_state')
            info['target']['humidity'] = self.data.get('device').get(serial_number).get('target_humidity')
            info['target']['humidity_enabled'] = self.data.get('device').get(serial_number).get('target_humidity_enabled')

        return info

    def get_energy_latest(self, serial_number=None):
        raise NotImplementedError()

    def turn_off(self, serial_number=None):
        raise NotImplementedError()

    def set_away(self, serial_number=None):
        raise NotImplementedError()

    def get_devices(self, device_type='thermostat'):
        self.get_status()

        if device_type == 'protect':
            return [p.get('serial_number') for p in self.data.get('topaz')]

        structures = self.data.get('user').get(self.user_id).get('structures')
        structure = structures[0]
        structure_id = structure.split('.')[1]
        devices = self.data.get('structure').get(structure_id).get('devices')

        return [device.split('.')[1] for device in devices]

    def get_default_serial(self, serial_number=None):
        if serial_number is None:
            devices_serials = self.get_devices()
            if not devices_serials:
                devices_serials = self.get_devices(device_type='protect')

            serial_number = devices_serials[0]

        return serial_number

    def get_default_device(self):
        serial_number = self.get_default_serial()
        return self.data.get('device').get(serial_number)

    def get_device_network_info(self, serial_number=None):
        self.get_status()
        serial_number = self.get_default_serial(serial_number)
        connection_info = self.data.get('track').get(serial_number)

        network_info = {}
        network_info['online'] = connection_info.get('online')
        network_info['last_connection'] = datetime.fromtimestamp(connection_info.get('last_connection') / 1000)
        network_info['wan_ip'] = connection_info.get('last_ip')
        network_info['local_ip'] = self.data.get('device').get(serial_number).get('local_ip')
        network_info['mac_address'] = self.data.get('device').get(serial_number).get('mac_address')

        return network_info
