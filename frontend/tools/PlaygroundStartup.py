import logging

# Set up logging for this script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("build123d").setLevel(logging.WARNING)  # Too noisy at INFO level

import micropip

# Fetch and run the upstream OCP.wasm bootstrap for build123d and its dependencies.
# This ensures we automatically stay up-to-date with the upstream bootstrap logic.
from pyodide.http import pyfetch

response = await pyfetch(
    "https://raw.githubusercontent.com/yeicor/OCP.wasm/master/build123d/bootstrap.py"
)
bootstrap_code = await response.string()
exec(bootstrap_code)

# Get the build123d version from the global scope (set by the caller)
# Default to "stable" if not provided
build123d_version = globals().get("_pg_build123d_version", "stable")

# Get the debug flag from the global scope (set by the caller)
# Default to False if not provided
debug = globals().get("_pg_debug", False)

# Get the constraints from the global scope (set by the caller)
# Default to None if not provided
constraints = globals().get("_pg_constraints", None)


async def mocked_hook():
    # Install the yacv_server package, which is the main server for the OCP.wasm playground.
    await micropip.install(
        "yacv_server",
        pre=True,
        reinstall=True,
        constraints=constraints.split("\n") if constraints else None,
    )

    # Preinstall the font-fetcher package and install its hook to automatically download any requested font.
    await micropip.install(
        "font-fetcher",
        pre=True,
        reinstall=True,
        constraints=constraints.split("\n") if constraints else None,
    )

    from font_fetcher.ocp import install_ocp_font_hook

    install_ocp_font_hook()


await bootstrap(
    build123d_version,
    debug=debug,
    constraints=constraints.split("\n") if constraints else None,
    mocked_hook=mocked_hook,
)

# Preimport the yacv_server package to ensure it is available in the global scope, and mock the ocp_vscode package.
from yacv_server import *

micropip.add_mock_package(
    "ocp-vscode",
    "3.4.0",
    modules={"ocp_vscode": "from yacv_server import *; show_object = show"},
)
show_object = show
