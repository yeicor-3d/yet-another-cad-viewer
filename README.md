# Yet Another CAD Viewer

A CAD viewer capable of displaying [OCP](https://github.com/CadQuery/OCP)
models ([CadQuery](https://github.com/CadQuery/cadquery)/[Build123d](https://github.com/gumyr/build123d)/...)
in a web browser.

## Features

- Cross-platform: works on any modern web browser.
- All [GLTF 2.0](https://www.khronos.org/gltf/) features (textures, PBR materials, animations...).
- All [model-viewer](https://modelviewer.dev/) features (smooth controls, augmented reality...).
- Load multiple models at once, load external models and even images as quads.
- View and interact with topological entities: faces, edges, vertices and locations.
- Control clipping planes and transparency of each model.
- Select any entity and measure bounding box size and distances.
- Fully-featured [static deployment](#static-deployment): just upload the viewer and models to your server.
- [Live lazy updates](#live-updates) while editing the CAD model (using the `yacv-server` package).

## Usage & demo

The [logo](yacv_server/logo.py) also works as an example of how to use the viewer.

### Live updates

To see the live updates you will need to run the [yacv_server](yacv_server) and
open [the viewer](https://yeicor-3d.github.io/yet-another-cad-viewer/) with
the `preload=ws://<host>:32323/` query parameter (by default it already tries localhost).

Note that [yacv_server](yacv_server) also hosts the frontend at `http://localhost:32323/` if you have no access to the
internet.

### Static deployment

To deploy the viewer and models as a static website you can simply copy the latest build directory to your server.
To load models use the `preload=...` query parameter in the URL.
It can be set multiple times to load multiple models.

Note that you can simply reuse the [main deployment](https://yeicor-3d.github.io/yet-another-cad-viewer/) and host only
your own models (linking them from the viewer with the `preload` query parameter).

To see a working example of a static deployment you can check out
the [demo](https://yeicor-3d.github.io/yet-another-cad-viewer/?preload=base.glb&preload=fox.glb&preload=img.jpg.glb&preload=location.glb)
(or
the [demo without animation](https://yeicor-3d.github.io/yet-another-cad-viewer/?autoplay=false&preload=base.glb&preload=fox.glb&preload=img.jpg.glb&preload=location.glb)).

![Demo](assets/screenshot.png)
