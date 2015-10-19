Arteria-Runfolder
=================

A self contained (Tornado) REST service for managing runfolders.

**Try it out:**

Install using pip:

    pip install -r requirements/dev . # possible add -e if you're in development mode.

Open up the `config/app.config` and specify the root directories that you want to monitor for runfolders. Then run:

    runfolder-ws --port 9999 --configroot config/

This will star the runfolder service on port 9999, and the api dock will be available under `localhost:9999/api`.
Try curl-ing to see what you can do with it:

    curl localhost:9999/api

**Running the tests**
After install you could run the integration tests to see if everything works as expected:
    ./runfolder_tests/run_integration_tests.py

This will by default start a local server, run the integration tests on it and then shut the server down.

Alternatively, you can run the same script against a remote server, specifying the URL and the runfolder directory:
    ./runfolder_tests/run_integration_tests.py http://testarteria1:10800/api/1.0 /data/testartera1/runfolders

Unit tests can be run with
    nosetests ./runfolder_tests/unit

**Install in production**
One way to install this as a daemon in a production environment
can be seen at https://github.com/arteria-project/arteria-provisioning
