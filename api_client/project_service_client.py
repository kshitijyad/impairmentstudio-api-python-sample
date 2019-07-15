import requests
import urllib.parse
from api_client.security import Session


class ProjectServiceClient(object):
    def __init__(self, session: Session, service_base_url):
        self.session = session
        self.service_base_url = service_base_url

    def run_analysis(self, analysis_id):
        url_path = f'/project/v1/analyses/{analysis_id}/jobs'
        url = urllib.parse.urljoin(self.service_base_url, url_path)

        response = requests.post(url, headers=self.session.get_auth_header(), proxies=self.session.proxies)
        response.raise_for_status()

        job_info = response.json()
        result = job_info['jobId']
        return result
