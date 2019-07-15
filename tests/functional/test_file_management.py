import pytest
import os
from api_client.file_management_service_client import FileManagementServiceClient
from api_client.security import Session
from pyhocon import ConfigFactory
from core import Expando


@pytest.fixture(scope='class')
def test_run_config():
    result = Expando()
    result.test_run_config = ConfigFactory.parse_file('test_run.conf')
    result.target_environments_settings = result.test_run_config['target_environments_settings']
    result.sso_service_base_url = result.target_environments_settings['sso_service_base_url']
    result.file_management_service_base_url = result.target_environments_settings['file_management_service_base_url']
    result.user_id = result.target_environments_settings['user_id']
    result.user_password = result.target_environments_settings['user_password']
    return result


@pytest.fixture(scope='function')
def file_management_client(test_run_config):
    session = Session(test_run_config.user_id, test_run_config.user_password, test_run_config.sso_service_base_url)
    result = FileManagementServiceClient(session, test_run_config.file_management_service_base_url)
    return result


class TestFileManagementClient():
    def test_upload_file__download_to_file__delete(self, file_management_client):
        source_file_path = 'file_a.csv'
        source_file_size = os.path.getsize(source_file_path)

        file_infos = file_management_client.import_file(source_file_path, 'file_a.csv', 'test_filemanagement_client')
        assert file_infos is not None
        assert len(file_infos) == 1 is not None

        file_info  = file_infos[0]
        assert file_info is not None
        assert file_info['filename'] == 'file_a.csv'
        assert file_info['path'] == 'raw'
        assert file_info['id'] == f'file_a_{file_info["serviceTimestamp"]}.csv'
        assert file_info['size'] == source_file_size
        assert file_info['status'] == True
        #  assert file_info['user'] == file_management_client.session.user_id
