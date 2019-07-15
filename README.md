# ImpairmentStudio™ Analysis API
This package contains sample code to call public API of ImpairmentStudio™ product. It simplifies some aspects of authentication on the client side including expired authentication token; provides wrappers to each service, including configuration; and it provides an example of analysis run workflow.

## Major modules
| Module Name | Description |
| ----------- | ----------- |
| impairment_studio_analytics.py | Contains an example of analysis run workflow with command line arguments and configuration |
| api_client/*_clients.py | Contains clients to public ImpairmentStudio™ services (API) |
| api_client/security.py | Handles authentication on the client side |

## Running analysis workflow from command line
```
python impairment_studio_analytics.py ^
  --analysis_id ANALYSIS_ID ^
  --input_zip_file INPUT_ZIP_FILE ^
  --result_files_dir RESULT_FILES_DIR ^
  --error_files_dir ERROR_FILES_DIR
```

## Command line arguments description
| Argument name | Description |
| ----------- | ----------- |
|analysis_id|The analysis id|
|input_zip_file|The name of the analysis input ZIP file|
|result_files_dir|The name of the results files directory|
|error_files_dir|The name of the error files directory|

## Analysis workflow configuration

The analysis workflow configuration is stored in the files impairment_studio_analytics.conf and impairment_studio_analytics_prd_data.conf

In order to run analysis workflow, two configuration parameters 'user_id' and 'user_password' must be provided based on the client's subscription to the ImpairmentStudio™ services.

These two parameters either can be simply replaced in the file impairment_studio_analytics_prd_data.conf or can be specified via environment variables before analysis run:

```
SET USER_ID_ENV=actual_user_id
SET USER_PASSWORD_ENV=actual_user_password

python impairment_studio_analytics.py ^
  --analysis_id ANALYSIS_ID ^
  --input_zip_file INPUT_ZIP_FILE ^
  --result_files_dir RESULT_FILES_DIR ^
  --error_files_dir ERROR_FILES_DIR
```

The configuration is handled by pyhocon package (https://github.com/chimpler/pyhocon; https://pypi.org/project/pyhocon) which is based on the HOCON specification (https://github.com/lightbend/config/blob/master/HOCON.md)

## Proxy Settings
If your network requires proxy settings, they should be specified either in the impairment_studio_analytics_prd_data.conf file or as environment variables (see example below).

```
SET HTTP_PROXY=[http_proxy_address]
SET HTTPS_PROXY=[https_proxy_address]
```

## Dependencies
All non-standard Python packages are listed in requirements.txt file.


