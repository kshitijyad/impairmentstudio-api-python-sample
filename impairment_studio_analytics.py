from pyhocon import ConfigFactory, ConfigMissingException
from api_client.security import Session
from api_client.file_management_service_client import FileManagementServiceClient
from api_client.dictionary_service_client import DictionaryServiceClient
from api_client.job_service_client import JobServiceClient
from api_client.project_service_client import ProjectServiceClient
from datetime import datetime
from datetime import timedelta
import time
import os
import argparse
import logging


# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s\t%(asctime)s\t%(filename)s\t%(message)s',
    datefmt="%Y-%m-%d %H:%M:%S"
)


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


# Load analytics run configuration
analytics_run_config = ConfigFactory.parse_file('impairment_studio_analytics.conf')
SSO_SERVICE_BASE_URL = analytics_run_config['sso_service_base_url']
DATA_API_BASE_URL = analytics_run_config['data_api_base_url']
IMPAIRMENT_STUDIO_API_BASE_URL = analytics_run_config['impairment_studio_api_base_url']
USER_ID = analytics_run_config['user_id']
USER_PASSWORD = analytics_run_config['user_password']
DEFAULT_JOB_WAIT_TIMEOUT = timedelta(minutes=analytics_run_config['default_job_wait_timeout_in_minutes'])
PROXIES = get_proxies(analytics_run_config)


def run_analytics(analysis_id, input_zip_file_path, result_files_dir, error_files_dir):
    """
    Runs analysis workflow
    :param analysis_id: Analysis id.
    :param input_zip_file_path: Input file in ZIP format
    :param result_files_dir: Output directory for results
    :param error_files_dir: Output directory for errors of the failed analysis runs or with errors.
    It can be the same as result_files_dir
    """
    logging.info(f"Analysis run (analysis id: '{analysis_id}') has started.")
    try:
        # Run analysis workflow in the scope of the same authentication session
        with Session(USER_ID, USER_PASSWORD, SSO_SERVICE_BASE_URL, PROXIES) as session:
            # Step 1: Upload ZIP file with inputs to the system's raw files location
            logging.info(f"Importing of the input file '{input_zip_file_path}' to the system has started.")
            fms_client = FileManagementServiceClient(session, DATA_API_BASE_URL)
            head, file_management_file_name = os.path.split(input_zip_file_path)
            files_info = fms_client.import_file(input_zip_file_path, file_management_file_name, 'raw')
            logging.info(f"Importing of the input file '{input_zip_file_path}' to the system has finished.")

            # Step 2.1: Schedule a job to move files from raw files location to processing location
            file_info = files_info[0]
            ds_client = DictionaryServiceClient(session, DATA_API_BASE_URL)
            job_id = ds_client.import_file(file_info['id'], 'FileUpload', True)
            logging.info(
                f"Moving input file '{file_info['filename']}' from raw files location "
                f"to the processing location has started (job id: '{job_id}').")

            # Step 2.2: Wait until file moving is done
            job_final_status = job_wait(session, job_id)
            # Step 2.3: Validate job status. If job failed, stop processing and log error.
            validate_job(job_id, job_final_status, fms_client, error_files_dir)
            logging.info(
                f"Moving input file '{file_info['filename']}' from raw files location "
                f"to the processing location has finished (job id: '{job_id}').")

            # Step 3.1: Schedule calculation job
            ps_client = ProjectServiceClient(session, IMPAIRMENT_STUDIO_API_BASE_URL)
            analysis_job_id = ps_client.run_analysis(analysis_id)
            logging.info(f"Analysis calculation (job id: '{analysis_job_id}') has started.")

            # Step 3.2: Wait until calculation is done
            analysis_job_final_status = job_wait(session, analysis_job_id)
            # Step 3.1: Validate job status. If job failed, stop processing and log error.
            validate_job(analysis_job_id, analysis_job_final_status, fms_client, error_files_dir)
            logging.info(f"Analysis calculation (job id: '{analysis_job_id}') has finished. ")

            # Step 4: Download results
            logging.info(f"Downloading analysis results to the folder '{result_files_dir}' has started.")
            destination_results_file_name = \
                f"job_{analysis_job_final_status['type']}_{analysis_job_final_status['qualifier']}_results.zip"
            destination_results_file_path = os.path.join(result_files_dir, destination_results_file_name)
            fms_client.download_analysis_result_file(analysis_id, destination_results_file_path)
            logging.info(
                f"Downloading analysis results to the file '{destination_results_file_path}' "
                f"in the folder '{result_files_dir}' has finished.")
            logging.info(f"Analysis run (analysis id: '{analysis_id}') has finished.")
    except Exception as e:
        logging.info(
            f"Analysis run (analysis id: '{analysis_id}') has been terminated by error: '{e}'.")


def job_wait(session, job_id, wait_timeout: timedelta = DEFAULT_JOB_WAIT_TIMEOUT):
    """
    Waits until job is complete successfully or with failures.
    :param session: Authentication session
    :param job_id: Job id
    :param wait_timeout: Wait time on the client side in seconds.
    :return: Job final status
    """
    wait_begin_datetime = datetime.now()
    js_client = JobServiceClient(session, IMPAIRMENT_STUDIO_API_BASE_URL)

    while datetime.now() <= wait_begin_datetime + wait_timeout:
        result = js_client.get_job(job_id)
        if result['status'] != 'RUNNING':
            return result
        # Put less load on the job service. Make a delay before the next call
        time.sleep(10)

    raise RunAnalyticsError(f"Job wait has been terminated by timeout. Job id: {job_id}; timeout: {wait_timeout}.")


def validate_job(job_id, job_final_status, fms_client, error_files_dir):
    """
    Validates job for failed statues and downloads errors to the defined directory
    :param job_id: Job id
    :param job_final_status: The final status of the job to validate
    :param fms_client: File management service client for downloading an error file
    :param error_files_dir: Destination directory for error files on the client side
    """
    if is_job_failed(job_final_status):
        destination_error_file_path = download_error_file(job_id, job_final_status, fms_client, error_files_dir)
        destination_error_file_abs_path = os.path.abspath(destination_error_file_path)
        raise RunAnalyticsError(
            f"The job 'job type: {job_final_status['type']}; job id: {job_id}' "
            f"stopped by error with status '{job_final_status['status']}'. "
            f"The errors are in the file '{destination_error_file_abs_path}'.")


def is_job_failed(job_status):
    """
    Check job status on failure
    :param job_status: Job status to verify
    :return: True - job has failed; False - job has finished successfully
    """
    job_failed_statuses = ['FAILED', 'COMPLETED_WITH_ERRORS']
    if job_status['status'] in job_failed_statuses:
        return True
    return False


def download_error_file(job_id, job_final_status, fms_client, error_files_dir):
    """
    Downloads error file for the failed jobs or jobs with calculation errors
    :param job_id: Job id
    :param job_final_status: The final status of the job
    :param fms_client: File management service client for downloading an error file
    :param error_files_dir: Destination directory for error files on the client side
    :return: Destination error file path (full name of the file)
    """
    destination_error_file_name = f"job_{job_final_status['type']}_{job_id}_errors.zip"
    destination_error_file_path = os.path.join(error_files_dir, destination_error_file_name)
    fms_client.download_job_import_error_file(job_id, destination_error_file_path)

    return destination_error_file_path


class RunAnalyticsError(Exception):
    """
    Run analysis error
    """
    pass


# Command line arguments parser definitions
args_parser = argparse.ArgumentParser()
args_parser.add_argument('--analysis_id', help='The analysis id.')
args_parser.add_argument('--input_zip_file', help="The name of the analysis input ZIP file.")
args_parser.add_argument('--result_files_dir', help="The name of the results files directory.")
args_parser.add_argument('--error_files_dir', help="The name of the error files directory.")

# Command line interface for run analysis workflow
if __name__ == '__main__':
    # Parse command line arguments
    args = args_parser.parse_args()
    arg_analysis_id = args.analysis_id
    arg_input_zip_file_path = args.input_zip_file
    arg_result_files_dir = args.result_files_dir
    arg_error_files_dir = args.error_files_dir

    # Run analysis workflow
    run_analytics(arg_analysis_id, arg_input_zip_file_path, arg_result_files_dir, arg_error_files_dir)
