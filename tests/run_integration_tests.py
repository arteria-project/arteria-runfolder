#!/usr/bin/python
import socket
import subprocess
import os
import time


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


def run_integration_tests():
    helper = IntegrationTestHelper()
    port = helper.find_port()
    os.environ['ARTERIA_RUNFOLDER_SVC_URL'] = "http://localhost:{}/api/1.0".format(port)

    # Run the service with the integration test config files
    directory = os.path.dirname(os.path.realpath(__file__))
    configroot = os.path.join(directory, "integration", "config")
    args = ["runfolder-ws", "--port", str(port), "--debug", "--configroot", configroot]
    service = subprocess.Popen(args)

    print "Waiting for process to start listening on port {}".format(port)
    helper.wait_for_listening(port)

    # Run all tests
    integration_root = os.path.join(directory, "integration")
    tests_process = subprocess.Popen(["nosetests", integration_root])
    tests_process.wait()
    print "Tests have finished running"

    print "Terminating the web service"
    service.terminate()

if __name__ == "__main__":
    run_integration_tests()

