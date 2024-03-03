import os
import subprocess

if __name__ == "__main__":
    if os.getenv('SKIP_BUILD_FRONTEND') is None:
        # When building the backend, make sure the frontend is built first
        subprocess.run(['yarn', 'install'], check=True)
        subprocess.run(['yarn', 'build', '--outDir', 'yacv_server/frontend'], check=True)
