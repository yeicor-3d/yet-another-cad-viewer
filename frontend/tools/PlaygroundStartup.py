import micropip

# Prioritize the OCP.wasm package repository for finding the ported dependencies.
micropip.set_index_urls(["https://yeicor.github.io/OCP.wasm", "https://pypi.org/simple"])

# For build123d < 0.10.0, we need to install the mock the py-lib3mf package (before the main install).
await micropip.install("lib3mf")
micropip.add_mock_package("py-lib3mf", "2.4.1", modules={"py_lib3mf": 'from lib3mf import *'})

# Install the yacv_server package, which is the main server for the OCP.wasm playground; and also preinstalls build123d.
await micropip.install("yacv_server")

# Preimport the yacv_server package to ensure it is available in the global scope, and mock the ocp_vscode package.
from yacv_server import *
micropip.add_mock_package("ocp-vscode", "2.8.9", modules={"ocp_vscode": 'from yacv_server import *'})
show_object = show

# Preinstall a font to avoid issues with no font being available.
def install_font_to_ocp(font_url, font_name=None):
    # noinspection PyUnresolvedReferences
    from pyodide.http import pyfetch
    from OCP.Font import Font_FontMgr, Font_SystemFont, Font_FA_Regular
    from OCP.TCollection import TCollection_AsciiString
    import os, asyncio

    font_name = font_name if font_name is not None else font_url.split("/")[-1]

    # Choose a "system-like" font directory
    font_path = os.path.join("/tmp", font_name)
    os.makedirs(os.path.dirname(font_path), exist_ok=True)

    # Download the font using pyfetch
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(pyfetch(font_url))
    font_data = loop.run_until_complete(response.bytes())

    # Save it to the system-like folder
    with open(font_path, "wb") as f:
        f.write(font_data)

    mgr = Font_FontMgr.GetInstance_s()
    font_t = Font_SystemFont(TCollection_AsciiString(font_path))
    font_t.SetFontPath(Font_FA_Regular, TCollection_AsciiString(font_path))
    assert mgr.RegisterFont(font_t, False)
    #print(f"✅ Font installed at: {font_path}")
    return font_path


# Make sure there is at least one font installed, so that the tests can run
install_font_to_ocp("https://raw.githubusercontent.com/xbmc/xbmc/d3a7f95f3f017b8e861d5d95cc4b33eef4286ce2/media/Fonts/arial.ttf")
