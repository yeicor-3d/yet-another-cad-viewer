# Quickstart of Yet Another CAD Viewer

## Installation

1. Download the contents of this folder.
2. Assuming you have a recent version of Python installed, install the required packages:

```bash
python -m venv venv
pip install -r requirements.txt
# Do this every time you change the terminal:
. venv/bin/activate
```

## Usage

### Development with hot-reloading

To start the viewer, open the [GitHub Pages link](https://yeicor-3d.github.io/yet-another-cad-viewer/) of the frontend.
It will try to connect to the server at `127.0.0.1:32323` by default (this can be changed with the `preload` query
parameter).

Running `python object.py` is enough to push the model to the viewer. However, the recommended way for developing with
minimal latency is to run in cell mode (#%%). This way, the slow imports are only done once, and the server keeps
running. After editing the file you can just re-run the cell with the `show_object` call to push the changes to
the viewer.

### Static final deployment

Once your model is complete, you may want to share it with others using the same viewer.

You can do so by exporting the model as a .glb file as a last step of your script.
This is already done in `object.py` if the environment variable `CI` is set.

Once you have the `object.glb` file, you can host it on any static file server and share the following link with others:
`https://yeicor-3d.github.io/yet-another-cad-viewer/?preload=<link-to-object.glb>`

For the example model, the build process is set up in [build.yml](../.github/workflows/build.yml), the upload process
is set up in [deploy.yml](../.github/workflows/deploy.yml), and the final link is:
https://yeicor-3d.github.io/yet-another-cad-viewer/?preload=example.glb

