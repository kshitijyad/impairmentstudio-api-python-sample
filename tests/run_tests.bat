cd %~dp0/functional
SET PYTHONPATH=../../

python -m pytest --junitxml=../test_run_reports/functional_tests_run_report.xml

cd %~dp0/unit
SET PYTHONPATH=../../
python -m pytest --junitxml=../test_run_reports/unit_tests_run_report.xml

cd ../
