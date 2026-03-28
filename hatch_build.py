import os
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface  # type: ignore


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        """Initialize the build hook and build the frontend if needed."""
        # Check if frontend build is disabled
        if os.environ.get("YACV_SKIP_FRONTEND_BUILD") == "true":
            self.app.display_info(
                "Frontend build disabled via YACV_SKIP_FRONTEND_BUILD"
            )
            return

        # Get the project root directory
        project_root = Path(self.root)
        frontend_dir = project_root / "yacv_server" / "frontend"

        # Check if frontend is already built
        if frontend_dir.exists() and any(frontend_dir.glob("**/*.js")):
            self.app.display_info("Frontend already built, skipping...")
            self._add_frontend_to_build_data(build_data, frontend_dir)
            return

        # Check if we have the necessary files to build the frontend
        package_json = project_root / "package.json"
        if not package_json.exists():
            self.app.display_info(
                "package.json not found, skipping frontend build. "
                "Frontend must be pre-built or included separately."
            )
            return

        self.app.display_info("Building frontend...")

        # Build frontend using npx yarn (available via npm)
        try:
            # Install dependencies
            self.app.display_info("Installing frontend dependencies...")
            subprocess.run(
                ["npx", "yarn", "install"],
                cwd=str(project_root),
                check=True,
            )

            # Build frontend
            self.app.display_info("Building frontend with Vite...")
            env = os.environ.copy()
            env["YACV_SMALL_BUILD"] = "true"
            subprocess.run(
                ["npx", "yarn", "build", "--outDir", str(frontend_dir)],
                cwd=str(project_root),
                check=True,
                env=env,
            )

            self.app.display_info("Frontend built successfully!")

            # Add frontend files to the build data so they get included in the wheel
            self._add_frontend_to_build_data(build_data, frontend_dir)

        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Failed to build frontend: {e}")
            raise
        except FileNotFoundError:
            self.app.display_error(
                "npx not found. Please install Node.js and npm to build the frontend."
            )
            raise

    def _add_frontend_to_build_data(self, build_data, frontend_dir):
        """Add frontend files to the build data for inclusion in the wheel."""
        if not frontend_dir.exists():
            return

        # Ensure the wheel has frontend files included
        if "force_include" not in build_data:
            build_data["force_include"] = {}

        # Add the entire frontend directory
        frontend_dir_str = str(frontend_dir)
        build_data["force_include"][frontend_dir_str] = "yacv_server/frontend"

        self.app.display_info(
            f"Added frontend directory to build data: {frontend_dir_str}"
        )
