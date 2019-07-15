import requests
import urllib.parse
import datetime
import jwt
import time
import logging


SSO_SVCS_BASE_URL = "https://sso.moodysanalytics.com"
AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS = 30


class AuthenticationError(Exception):
    pass


class Session(object):
    def __init__(self, user_id: str, user_password: str, sso_svcs_base_url: str = SSO_SVCS_BASE_URL, proxies={}):
        self.sso_svcs_base_url = sso_svcs_base_url
        self.user_id = user_id
        self.user_password = user_password
        self.proxies = proxies

        self.auth_token = None
        self.auth_token_claimset = None
        self.expiration_timestamp = None
        self.expiration_datetime = None

    def __enter__(self):
        self.get_auth_token()
        logging.info(f"Security token has been generated.")

        return self

    def __exit__(self, *args):
        self.close()

    def get_auth_token(self):
        # Get authentication token for the first time
        if self.auth_token is None:
            self.auth_token = self.request_new_auth_token()
            self.update_auth_token_claimset_expiration_info()
            return self.auth_token

        # If it's a renewal time, renew authentication token
        if self.is_auth_token_renewal():
            try:
                self.auth_token = self.renew_auth_token()
                self.update_auth_token_claimset_expiration_info()
                return self.auth_token
            except AuthenticationError:
                # It can happen if token is fully expired. In this case, request new token
                self.auth_token = self.request_new_auth_token()
                self.update_auth_token_claimset_expiration_info()
                return self.auth_token

        # Token has not expired
        result = self.auth_token
        return result

    def close(self):
        if self.auth_token is None:
            return

        self.revoke_auth_token()

    def request_new_auth_token(self):
        url_path = '/sso-api/v1/token'
        url = urllib.parse.urljoin(self.sso_svcs_base_url, url_path)

        request_new_auth_token_data = {
            'username': self.user_id,
            'password': self.user_password,
            'grant_type': 'password',
            'scope': 'openid'
        }

        response = requests.post(
            url,
            data=request_new_auth_token_data,
            auth=(self.user_id, self.user_password),
            proxies=self.proxies
        )
        response.raise_for_status()

        response_body_json = response.json()
        result = response_body_json.get('id_token')
        if result is None or result == "":
            raise AuthenticationError(
                f"Authorization token is empty. "
                f"Authentication token has not been retrieved from "
                f"SSO service '{self.sso_svcs_base_url} for user '{self.user_id}''.")

        token_type = response_body_json.get('token_type')
        if token_type != 'Bearer':
            raise AuthenticationError(f"Wrong token type '{token_type}'. Expected token type is 'Bearer'.")

        return result

    def delete_auth_token(self, auth_token):
        url_path = '/sso-api/v1/token'
        url = urllib.parse.urljoin(self.sso_svcs_base_url, url_path)

        response = requests.delete(url, headers=Session.create_auth_header(auth_token), proxies=self.proxies)
        response.raise_for_status()

    def revoke_auth_token(self):
        self.delete_auth_token(self.auth_token)

        self.auth_token = None
        self.auth_token_claimset = None
        self.expiration_timestamp = None
        self.expiration_datetime = None

    def renew_auth_token(self):
        # Revoke current token
        self.revoke_auth_token()

        # Wait for one second for token revocation process
        time.sleep(1)

        # Request a new token
        result = self.request_new_auth_token()
        return result

    def update_auth_token_claimset_expiration_info(self):
        self.auth_token_claimset = jwt.decode(self.auth_token, verify=False)
        self.expiration_timestamp = self.auth_token_claimset['exp']
        self.expiration_datetime = datetime.datetime.fromtimestamp(self.expiration_timestamp)

    def is_auth_token_renewal(self):
        if self.expiration_datetime is None:
            raise AuthenticationError(
                "Error checking renewal time of the authentication token. "
                "The token's expiration date/time is empty. "
                "Get authentication token calling get_auth_token() first.")

        time_left = self.expiration_datetime - self.get_current_date_time()

        if time_left.days == -1:
            return True

        if time_left.seconds < AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS:
            return True

        return False

    def get_auth_header(self):
        auth_token = self.get_auth_token()
        result = Session.create_auth_header(auth_token)
        return result

    @staticmethod
    def get_current_date_time():
        result = datetime.datetime.now()
        return result

    @staticmethod
    def remove_prefix_bearer(bearer_token):
        result = Session.remove_prefix(bearer_token, 'Bearer ')
        if not len(result) > 0:
            raise AuthenticationError('Bearer authentication token is empty.')
        return result

    @staticmethod
    def remove_prefix(text, prefix):
        if not text.startswith(prefix):
            return text
        result = text[len(prefix):]
        return result

    @staticmethod
    def create_auth_header(auth_token):
        result = {'Authorization': f'Bearer {auth_token}'}
        return result
