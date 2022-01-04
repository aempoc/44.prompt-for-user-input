import requests
from http_exceptions import BadRequestException, UnauthorizedException, NotFoundException
from requests.auth import HTTPBasicAuth

class JIRA:
    API_URL = 'rest/api/3/'

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    def get_all_projects(self, params=None):
        return self._get(self.API_URL + 'project', params=params)

    def create_issue(self, data, params=None):
        headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                    }
        return self._post(self.API_URL + 'issue', data=data, params=params, headers = headers)

    def add_attachment(self, key, data, params=None):
        headers = {
                        "Accept": "application/json",
                        "X-Atlassian-Token": "no-check"
                    }
        path = self.API_URL + 'issue/'+ key + '/attachments'
        response =  requests.request(
                        "POST",
                        self.host + path,
                        files=data,
                        headers=headers,
                        auth=HTTPBasicAuth(self.user, self.password)
            )
        return self._parse(response)
    def _get(self, path, params=None):
        response = requests.get(self.host + path, params=params, auth=(self.user, self.password))
        return self._parse(response)

    def _post(self, path, params=None, data=None, headers = None):
        response =  requests.request(
                        "POST",
                        self.host + path,
                        data=data,
                        headers=headers,
                        auth=HTTPBasicAuth(self.user, self.password)
            )
        return self._parse(response)

    def _parse(self, response):
        status_code = response.status_code
        if 'application/json' in response.headers['Content-Type']:
            try:
                r = response.json()
            except Exception as e:
                r = None
        else:
            r = response.text
        if status_code in (200, 201):
            return r
        if status_code == 204:
            return None
        message = None
        try:
            if 'errorMessages' in r:
                message = r['errorMessages']
        except Exception:
            message = 'No error message.'
        if status_code == 400:
            raise BadRequestException(message)
        if status_code == 401:
            raise UnauthorizedException(message)
        if status_code == 403:
            raise PermissionError(message)
        if status_code == 404:
            raise NotFoundException(message)
    