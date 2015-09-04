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
    




