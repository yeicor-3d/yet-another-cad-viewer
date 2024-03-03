import os
import subprocess

if __name__ == "__main__":
    # When building the backend, make sure the frontend is built first
    subprocess.run(['yarn', 'install'], check=True)
    subprocess.run(['yarn', 'build', '--dist-dir', 'yacv_server/frontend'], check=True)
