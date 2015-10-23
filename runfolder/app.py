from arteria.web.app import AppService
from runfolder.handlers import *


def start():
    """Entry point of the web service"""
    app_svc = AppService.create(__package__)
    runfolder_svc = RunfolderService(app_svc.config_svc)

    # Setup the routing. Help will be automatically available at /api, and will be based on
    # the doc strings of the get/post/put/delete methods
    args = dict(app_svc=app_svc, runfolder_svc=runfolder_svc, config_svc=app_svc.config_svc)
    routes = [
        (r"/api/1.0/runfolders", ListAvailableRunfoldersHandler, args),
        (r"/api/1.0/runfolders/next", NextAvailableRunfolderHandler, args),
        (r"/api/1.0/runfolders/path(/.*)", RunfolderHandler, args),
        (r"/api/1.0/runfolders/test/markasready/path(/.*)", TestFakeSequencerReadyHandler, args),
        (r"/api/1.0/admin/settings", SettingsHandler, args)  # TODO: Move to core
    ]
    app_svc.start(routes)

