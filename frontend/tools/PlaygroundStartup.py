import micropip

# Fetch and run the upstream OCP.wasm bootstrap for build123d and its dependencies.
# This ensures we automatically stay up-to-date with the upstream bootstrap logic.
from pyodide.http import pyfetch
response = await pyfetch("https://raw.githubusercontent.com/yeicor/OCP.wasm/master/build123d/bootstrap_in_pyodide.py")
bootstrap_code = await response.string()
exec(bootstrap_code)
await bootstrap()

# Install the yacv_server package, which is the main server for the OCP.wasm playground.
await micropip.install("yacv_server", pre=True)

# Preimport the yacv_server package to ensure it is available in the global scope, and mock the ocp_vscode package.
from yacv_server import *

micropip.add_mock_package("ocp-vscode", "2.8.9", modules={"ocp_vscode": 'from yacv_server import *'})
show_object = show

# Preinstall the font-fetcher package and install its hook to automatically download any requested font.
await micropip.install("font-fetcher", pre=True)

from font_fetcher.ocp import install_ocp_font_hook

install_ocp_font_hook()
