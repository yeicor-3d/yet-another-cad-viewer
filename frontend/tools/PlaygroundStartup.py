import micropip

# Prioritize the OCP.wasm package repository for finding the ported dependencies.
micropip.set_index_urls(["https://yeicor.github.io/OCP.wasm", "https://pypi.org/simple"])

# For build123d < 0.10.0, we need to install the mock the py-lib3mf package (before the main install).
await micropip.install("lib3mf")
micropip.add_mock_package("py-lib3mf", "2.4.1", modules={"py_lib3mf": 'from lib3mf import *'})

# Install the yacv_server package, which is the main server for the OCP.wasm playground; and also preinstalls build123d.
await micropip.install("yacv_server", pre=True)

# Preimport the yacv_server package to ensure it is available in the global scope, and mock the ocp_vscode package.
from yacv_server import *

micropip.add_mock_package("ocp-vscode", "2.8.9", modules={"ocp_vscode": 'from yacv_server import *'})
show_object = show

# Preinstall the font-fetcher package and install its hook to automatically download any requested font.
await micropip.install("font-fetcher", pre=True)

from font_fetcher.ocp import install_ocp_font_hook

install_ocp_font_hook()
