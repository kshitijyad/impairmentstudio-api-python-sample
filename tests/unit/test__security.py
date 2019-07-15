import pytest
from pyhocon import ConfigFactory, ConfigMissingException
from api_client.security import Session
from api_client.security import AuthenticationError


class TestSession():
    DUMMY_USER_ID = 'USER_ID'
    DUMMY_USER_PASSWORD = 'USER_PASSWORD'

    @pytest.mark.parametrize('user_id, user_password, sso_svcs_base_url', [
        ('user_abc',
         'user_abc_password',
         'https://sso.moodysanalytics.com'),
        ('user_abc',
         'user_abc_password',
         'https://new-sso.moodysanalytics.com'),
        ('user_abc',
         'user_abc_password',
         None)
    ])
    def test_init(self, user_id, user_password, sso_svcs_base_url):
        target = Session(user_id, user_password)
        assert target.user_id == user_id
        assert target.user_password == user_password
        assert target.sso_svcs_base_url == 'https://sso.moodysanalytics.com'
        assert target.auth_token is None

        target = Session(user_id, user_password, sso_svcs_base_url)
        assert target.user_id == user_id
        assert target.user_password == user_password
        assert target.sso_svcs_base_url == sso_svcs_base_url
        assert target.auth_token is None


    @pytest.mark.parametrize('bearer_token, expected', [
        ('Bearer AUTH_TOKEN',
         'AUTH_TOKEN')
    ])
    def test_remove_prefix_bearer(self, bearer_token, expected):
        actual = Session.remove_prefix_bearer(bearer_token)
        assert actual == expected

    @pytest.mark.parametrize('bearer_token, expected_error_message', [
        ('Bearer ',
         'Bearer authentication token is empty.')
    ])
    def test_errors_remove_prefix_bearer(self, bearer_token, expected_error_message):
        target = Session(TestSession.DUMMY_USER_ID, TestSession.DUMMY_USER_PASSWORD)
        with pytest.raises(AuthenticationError) as exception_info:
            target.remove_prefix_bearer(bearer_token)

        actual_error_message = str(exception_info.value)
        assert actual_error_message == expected_error_message


    @pytest.mark.parametrize('text, prefix, expected', [
        ('prefix Lorem ipsum dolor.',
         'prefix ',
         'Lorem ipsum dolor.'),
        ('prefix ',
         'prefix ',
         ''),
        ('Lorem ipsum dolor.',
         '',
         'Lorem ipsum dolor.'),
    ])
    def test_remove_prefix(self, text, prefix, expected):
        actual = Session.remove_prefix(text, prefix)
        assert actual == expected


    @pytest.mark.parametrize('auth_token, expected', [
        ('eyJ4NXQiOiJObU...g6MRf8-U0DJBM',
         'Bearer eyJ4NXQiOiJObU...g6MRf8-U0DJBM')
    ])
    def test_create_auth_header(self, auth_token, expected):
        actual = Session.create_auth_header(auth_token)
        assert actual['Authorization'] == expected

    def test_request_new_auth_token(self):
        test_run_conf = ConfigFactory.parse_file('test_run.conf')

        sso_service_base_url = test_run_conf['sso_service_base_url']
        user_id = test_run_conf['user_id']
        user_password = test_run_conf['user_password']

        proxies = get_proxies(test_run_conf)

        target = Session(user_id, user_password, sso_service_base_url, proxies)
        actual = target.request_new_auth_token()

        assert actual is not None


def get_proxies(config):
    result = {}

    append_proxy_form_config(result, 'http', config, 'http_proxy')
    append_proxy_form_config(result, 'https', config, 'https_proxy')

    return result


def append_proxy_form_config(proxies, proxy_name, config, config_item_name):
    proxy = get_config_item(config, config_item_name)
    if proxy is not None:
        proxies[proxy_name] = proxy


def get_config_item(config, item_name):
    try:
        result = config[item_name]
        return result
    except ConfigMissingException:
        return None


