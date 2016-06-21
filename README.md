Arteria-Runfolder
=================

A self contained (Tornado) REST service for managing runfolders.

Availabe on COPR. Install with:
dnf copr enable lef/arteria 
dnf install runfolder
(This will pull all required dependencies).

Start with:
systemctl runfolder start

**Running the tests**
After install you could run the integration tests to see if everything works as expected:
    ./runfolder_tests/run_integration_tests.py

This will by default start a local server, run the integration tests on it and then shut the server down.

Alternatively, you can run the same script against a remote server, specifying the URL and the runfolder directory:
    ./runfolder_tests/run_integration_tests.py http://testarteria1:10800/api/1.0 /data/testartera1/runfolders

Unit tests can be run with
    nosetests ./runfolder_tests/unit
