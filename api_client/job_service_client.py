import requests
import urllib.parse
from api_client.security import Session


class JobServiceClient(object):
    def __init__(self, session: Session, service_base_url):
        self.session = session
        self.service_base_url = service_base_url

    def get_job(self, job_id):
        url_path = f'/job/v1/jobs/{job_id}'
        url = urllib.parse.urljoin(self.service_base_url, url_path)
        response = requests.get(url, headers=self.session.get_auth_header(), proxies=self.session.proxies)
        response.raise_for_status()

        jobs_status = response.json()
        return jobs_status
