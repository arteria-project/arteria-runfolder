#!/usr/bin/python
import socket
import subprocess
import os
import time
import sys


class IntegrationTestHelper:
    @staticmethod
    def find_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        _, port = s.getsockname()
        s.close()
        return port

    @staticmethod
    def is_listening(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        return result == 0

    def wait_for_listening(self, port):
        while not self.is_listening(port):
            print "waiting"
            time.sleep(0.1)


def setup_local_server(port):
    """Starts a local server on an unused port and returns the process when the port
       starts listening"""

    # Run the service with the integration test config files
    directory = os.path.dirname(os.path.realpath(__file__))
    configroot = os.path.join(directory, "integration", "config")
    args = ["runfolder-ws", "--port", str(port), "--debug", "--configroot", configroot]
    try:
        service = subprocess.Popen(args)
    except OSError:
        print "Can't find 'runfolder-ws', it might not be installed or virtualenv not activated"
        raise

    print "Waiting for process to start listening on port {}".format(port)
    helper = IntegrationTestHelper()
    helper.wait_for_listening(port)

    return service


def run_integration_tests(url=None, directory=None):
    local_server = None
    if url is None:
        helper = IntegrationTestHelper()
        port = helper.find_port()
        url = "http://localhost:{}/api/1.0".format(port)
        local_server = setup_local_server(port)

    # Set the url as an environment variable that will be used by the tests:
    # This should rather be pushed in via a config file
    os.environ['ARTERIA_RUNFOLDER_SVC_URL'] = url

    if directory is not None:
        os.environ['ARTERIA_RUNFOLDER_MONITORED_DIR'] = directory

    # Run all tests
    directory = os.path.dirname(os.path.realpath(__file__))
    integration_root = os.path.join(directory, "integration")
    tests_process = subprocess.Popen(["nosetests", integration_root])
    tests_process.wait()
    print "Tests have finished running"

    if local_server is not None:
        print "Terminating the locally running web service"
        local_server.terminate()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    directory = sys.argv[2] if len(sys.argv) > 2 else None
    run_integration_tests(url, directory)

