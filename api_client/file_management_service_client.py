import requests
import urllib.parse
from api_client.security import Session


class FileManagementServiceClient(object):
    def __init__(self, session: Session, service_base_url):
        self.session = session
        self.service_base_url = service_base_url

    def import_file(self, source_file_path, file_management_file_name, file_management_file_path):
        url_path = "/fms/v1/files/job/import"
        url = urllib.parse.urljoin(self.service_base_url, url_path)
        files = {file_management_file_name: open(source_file_path, 'rb')}

        upload_data = {'path': file_management_file_path}
        response = requests.post(
            url,
            data=upload_data,
            files=files,
            headers=self.session.get_auth_header(),
            proxies=self.session.proxies)
        response.raise_for_status()

        result = response.json()
        return result

    def download_job_import_error_file(self, job_id, destination_file_path):
        file_content = self.retrieve_job_import_error_file_content(job_id)

        with open(destination_file_path, 'wb') as local_destination_file:
            local_destination_file.write(file_content)

    def retrieve_job_import_error_file_content(self, job_id):
        url_path = f'/fms/v1/files/job/import/{job_id}'
        url = urllib.parse.urljoin(self.service_base_url, url_path)

        response = requests.get(url, headers=self.session.get_auth_header(), proxies=self.session.proxies)
        response.raise_for_status()

        result = response.content
        return result

    def download_analysis_result_file(self, analysis_id, destination_file_path):
        file_content = self.retrieve_analysis_result_file_content(analysis_id)

        with open(destination_file_path, 'wb') as local_destination_file:
            local_destination_file.write(file_content)

    def retrieve_analysis_result_file_content(self, analysis_id):
        url_path = f'/fms/v1/files/job/analyses/{analysis_id}'
        url = urllib.parse.urljoin(self.service_base_url, url_path)

        response = requests.get(url, headers=self.session.get_auth_header(), proxies=self.session.proxies)
        response.raise_for_status()

        result = response.content
        return result
