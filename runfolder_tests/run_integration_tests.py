#!/usr/bin/python
import socket
import subprocess
import os
import time
import sys
import shutil
import stat

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


def execute(args, script_name=None):
    """
    Execute the args using Popen, but create and execute a corresponding
    script if script_name is provided
    """
    if script_name:
        with open(script_name, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(" ".join(args))
            f.write("\n")
        os.chmod(script_name, stat.S_IRWXU)
        service = subprocess.Popen([os.path.join(".", script_name)])
    else:
        service = subprocess.Popen(args)
    return service


def setup_testrun_dir():
    """
    Sets up a testrun_* directory in the cwd and returns the path to it
    """
    test_run = "testrun_{}".format(int(time.time()))
    os.mkdir(test_run)
    this_files_dir = os.path.dirname(os.path.realpath(__file__))
    config_templates = os.path.join(this_files_dir, "integration", "config")
    os.mkdir(os.path.join(test_run, "runfolders"))
    shutil.copy2(os.path.join(config_templates, "app.config"), test_run)
    shutil.copy2(os.path.join(config_templates, "logger.config"), test_run)
    return os.path.realpath(test_run)


def setup_local_server(port, dir):
    """
    Starts a local server on an unused port and returns the process when the port
    starts listening
    """

    old_dir = os.getcwd()
    os.chdir(dir)
    print "Running server locally on port {}, from dir {}".format(port, dir)
    service = execute(["runfolder-ws", "--port", str(port), "--debug", "--configroot", "."])

    print "Waiting for process to start listening on port {}".format(port)
    helper = IntegrationTestHelper()
    helper.wait_for_listening(port)
    os.chdir(old_dir)

    return service


def run_integration_tests(url, runfolder_directory, log_file_path):
    # Set the url as an environment variable that will be used by the tests:
    # This should rather be pushed in via a config file
    os.environ['ARTERIA_RUNFOLDER_SVC_URL'] = url

    if runfolder_directory is not None:
        os.environ['ARTERIA_RUNFOLDER_MONITORED_DIR'] = runfolder_directory

    if log_file_path is not None:
        os.environ['ARTERIA_RUNFOLDER_LOG_FILE'] = log_file_path

    # Run all tests
    directory = os.path.dirname(os.path.realpath(__file__))
    integration_root = os.path.join(directory, "integration")
    tests_process = subprocess.Popen(["nosetests", integration_root])
    tests_process.wait()
    print "Tests have finished running"


def run_integration_tests_locally():
    helper = IntegrationTestHelper()
    port = helper.find_port()
    url = "http://localhost:{}/api/1.0".format(port)
    test_run_dir = setup_testrun_dir()
    local_server = setup_local_server(port, test_run_dir)
    runfolder_directory = os.path.join(test_run_dir, "runfolders")
    log_file_path = os.path.join(test_run_dir, "runfolder.log")

    try:
        run_integration_tests(url, runfolder_directory, log_file_path)
    finally:
        if local_server is not None:
            print "Terminating the locally running web service"
            local_server.terminate()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    runfolder_directory = sys.argv[2] if len(sys.argv) > 2 else None

    if url is None:
        run_integration_tests_locally()
    else:
        run_integration_tests(url, runfolder_directory, None)

