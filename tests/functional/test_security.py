import pytest
import api_client.security as security
import datetime
from api_client.security import Session
from pyhocon import ConfigFactory
from core import Expando


@pytest.fixture(scope='class')
def test_run_configuration_manager():
    result = ConfigFactory.parse_file('test_run.conf')
    return result


@pytest.fixture(scope='class')
def test_run_config(test_run_configuration_manager):
    result = Expando()
    result.test_run_config = test_run_configuration_manager
    result.target_environments_settings = result.test_run_config['target_environments_settings']
    result.sso_service_base_url = result.target_environments_settings['sso_service_base_url']
    result.user_id = result.target_environments_settings['user_id']
    result.user_password = result.target_environments_settings['user_password']
    return result


@pytest.fixture(scope='function')
def session(test_run_config):
    result = Session(test_run_config.user_id, test_run_config.user_password, test_run_config.sso_service_base_url)
    return result


class TestSession:
    def test_get_auth_token(self, session):
        first_token = session.get_auth_token()
        actual = session.is_auth_token_renewal()
        assert actual == False

        # Second call to get_auth_token() has to return the same token because it expires in 15 minutes
        next_token = session.get_auth_token()
        assert next_token == first_token

    def test_close(self, session):
        auth_token = session.get_auth_token()
        assert auth_token == session.auth_token

        session.close()
        assert session.auth_token is None

        # Second call to close() shouldn't fail
        session.close()

    def test_context_manager(self, test_run_configuration_manager):
        target_environments_settings = test_run_configuration_manager['target_environments_settings']
        sso_service_base_url = target_environments_settings['sso_service_base_url']
        user_id = target_environments_settings['user_id']
        user_password = target_environments_settings['user_password']
        with Session(user_id, user_password, sso_service_base_url) as session:
            assert session.auth_token is not None, 'Session.__enter__ must initialize Session.auth_token'

            auth_token = session.get_auth_token()
            assert auth_token == session.auth_token

        assert session.auth_token is None

    def test_get_auth_token_about_to_expire(self, session, mocker):
        first_token = session.get_auth_token()
        assert session.is_auth_token_renewal() == False

        mocker.patch('api_client.security.Session.get_current_date_time')

        virtual_current_date_time = session.expiration_datetime - datetime.timedelta(seconds=security.AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS + 1)
        security.Session.get_current_date_time.return_value = virtual_current_date_time

        next_token = session.get_auth_token()
        assert next_token == first_token

    def test_get_auth_token_inside_renewal_threshold(self, session, mocker):
        first_token = session.get_auth_token()
        assert session.is_auth_token_renewal() == False

        mocker.patch('api_client.security.Session.get_current_date_time')

        virtual_current_date_time = session.expiration_datetime - datetime.timedelta(seconds=security.AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS - 1)
        security.Session.get_current_date_time.return_value = virtual_current_date_time

        next_token = session.get_auth_token()
        assert next_token != first_token

    def test_get_auth_token_beyond_expiration_datetime(self, session, mocker):
        first_token = session.get_auth_token()
        assert session.is_auth_token_renewal() == False

        mocker.patch('api_client.security.Session.get_current_date_time')

        virtual_current_date_time = session.expiration_datetime + datetime.timedelta(seconds=1)
        security.Session.get_current_date_time.return_value = virtual_current_date_time

        next_token = session.get_auth_token()
        assert next_token != first_token
