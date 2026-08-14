# Licensing and third-party components

This page describes the licensing of SVG to STL Web and the components that
the repository intentionally includes or installs. It is an inventory, not
legal advice. The version ranges are taken from `pyproject.toml`; the exact
versions and indirect dependencies in a particular container are those
resolved on the day that image was built.

## The short version

- The SVG to STL Web source written for this repository is available under
  the [MIT License](https://github.com/tonyjurg/svg2stl-web/blob/main/LICENSE).
- The project builds on the MIT-licensed approach in
  [MaxHalford/svg2stl](https://github.com/MaxHalford/svg2stl) and
  [avipars/svg2stl](https://github.com/avipars/svg2stl). Their original 2021
  copyright notice is preserved in this repository's `LICENSE` file.
- The conversion engine uses the separately licensed **Gmsh** Python wheel.
  Gmsh is GPL version 2 or later, with the exception stated in its official
  license. A Docker image containing Gmsh is therefore not an MIT-only
  distribution.
- The local 3D preview bundles **Three.js r185**, including `OrbitControls`
  and `STLLoader`, under the MIT License.
- Every other package retains its own license. The repository's MIT License
  does not replace any license listed below.

## What the Gmsh license means here

The application imports and calls the `gmsh` Python package to build and mesh
geometry. The wheel contains the Gmsh application and SDK and is distributed
under **GPL-2.0-or-later with the Gmsh exception**. The official license text
and exception are available from
[Gmsh](https://gmsh.info/LICENSE.txt), and source code is available from the
[Gmsh source repository](https://gitlab.onelab.info/gmsh/gmsh).

The repository can license its own independent source under MIT while Gmsh
retains its GPL license. Anyone redistributing a built wheel, container, NAS
package, or other bundle containing Gmsh must assess and meet the applicable
GPL obligations, including preservation of notices and corresponding-source
requirements. Gmsh also offers a commercial license for uses that require
different terms.

The GPL text says that program output is covered only when the output itself
constitutes a work based on the GPL-covered program. Merely converting a
user-provided SVG does not by itself make that SVG or the resulting STL a copy
of Gmsh. Copyright and other rights in uploaded artwork remain the user's
responsibility.

## Components shipped in the repository

| Component | Included files or purpose | Version | License |
| --- | --- | --- | --- |
| SVG to STL Web | Application, worker, Pages site, and documentation | Repository version | [MIT](https://github.com/tonyjurg/svg2stl-web/blob/main/LICENSE) |
| MaxHalford/svg2stl | Original SVG parsing and mesh-generation approach | Upstream lineage | [MIT](https://github.com/MaxHalford/svg2stl/blob/master/LICENSE) |
| avipars/svg2stl | Continued upstream implementation | Upstream lineage | [MIT](https://github.com/avipars/svg2stl/blob/master/LICENSE) |
| Three.js core | `three.module.min.js` and `three.core.min.js` | r185 / 0.185.1 | [MIT](https://github.com/mrdoob/three.js/blob/r185/LICENSE) |
| Three.js OrbitControls | `OrbitControls.js` | r185 / 0.185.1 | [MIT](https://github.com/mrdoob/three.js/blob/r185/LICENSE) |
| Three.js STLLoader | `STLLoader.js` | r185 / 0.185.1 | [MIT](https://github.com/mrdoob/three.js/blob/r185/LICENSE) |

The bundled Three.js license text is also retained locally as
`app/static/THREE-LICENSE.txt`.

## Python runtime components

These are every direct runtime requirement declared by the project.

| Component | Declared version | Purpose | License |
| --- | --- | --- | --- |
| [defusedxml](https://pypi.org/project/defusedxml/) | `>=0.7,<1` | Defused XML parsing primitives | PSF-2.0 |
| [FastAPI](https://pypi.org/project/fastapi/) | `>=0.116,<1` | HTTP application framework | MIT |
| [Gmsh](https://pypi.org/project/gmsh/) | `>=4.15,<5` | CAD geometry and mesh generation | GPL-2.0-or-later with Gmsh exception |
| [Jinja2](https://pypi.org/project/Jinja2/) | `>=3.1,<4` | Server-side HTML templating | BSD-3-Clause |
| [NumPy](https://pypi.org/project/numpy/) | `>=2,<3` | Numeric arrays and geometry data | BSD-3-Clause; distributions also carry component notices |
| [python-multipart](https://pypi.org/project/python-multipart/) | `>=0.0.20,<1` | Multipart SVG upload parsing | Apache-2.0 |
| [svg.path](https://pypi.org/project/svg.path/) | `>=7,<8` | SVG path parsing and sampling | MIT |
| [trimesh](https://pypi.org/project/trimesh/) | `>=4.12,<6` | STL loading and mesh validation | MIT |
| [Uvicorn](https://pypi.org/project/uvicorn/) | `>=0.35,<1` | ASGI web server | BSD-3-Clause |

The `uvicorn[standard]` installation can additionally select the following
platform-dependent extras. They are not copied into this repository, but are
installed into a normal production image when applicable.

| Component | Purpose | License |
| --- | --- | --- |
| [httptools](https://pypi.org/project/httptools/) | Accelerated HTTP parser | MIT |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Environment-file support | BSD-3-Clause |
| [PyYAML](https://pypi.org/project/PyYAML/) | YAML support | MIT |
| [uvloop](https://pypi.org/project/uvloop/) | Optional Unix event loop | MIT and Apache-2.0 components |
| [watchfiles](https://pypi.org/project/watchfiles/) | Development reload support | MIT |
| [websockets](https://pypi.org/project/websockets/) | WebSocket implementation | BSD-3-Clause |

FastAPI, Uvicorn, and the other direct requirements install additional
indirect Python packages. Because this project declares compatible version
ranges instead of a lock file, that exact transitive set can change between
builds. Each installed distribution includes its authoritative metadata and
license files in its `.dist-info` directory. Inspect the actual image when
preparing a redistribution rather than treating this page as a frozen bill of
materials.

## Development and verification components

These optional packages are installed by `requirements.txt` for linting and
tests, but are not installed by the production Dockerfile.

| Component | Declared version | Purpose | License |
| --- | --- | --- | --- |
| [HTTPX](https://pypi.org/project/httpx/) | `>=0.28,<1` | HTTP test client | BSD-3-Clause |
| [pytest](https://pypi.org/project/pytest/) | `>=8,<10` | Test runner | MIT |
| [PyYAML](https://pypi.org/project/PyYAML/) | `>=6,<7` | Workflow-file validation | MIT |
| [Ruff](https://pypi.org/project/ruff/) | `>=0.12,<1` | Linter and formatter | MIT |

GitHub Actions uses `actions/checkout`, `actions/setup-python`,
`actions/configure-pages`, `actions/upload-pages-artifact`, and
`actions/deploy-pages`. These CI actions run on GitHub's infrastructure; they
are build and publication tools and are not included in the application or
its Docker image. Their source repositories carry their own license notices.

## Container base and operating-system libraries

The production Dockerfile starts from `python:3.14-slim-bookworm`. That base
contains Python under the PSF License and a minimal Debian Bookworm userland
whose packages retain their individual licenses. The Dockerfile explicitly
adds the following Debian runtime packages required by Gmsh:

| Debian package | Purpose | Principal upstream license |
| --- | --- | --- |
| `libgl1` | OpenGL dispatch library | Permissive MIT-style licenses |
| `libglu1-mesa` | OpenGL Utility Library | SGI Free Software License B 2.0 and component notices |
| `libgomp1` | GNU OpenMP runtime | GPL-3.0-or-later with GCC Runtime Library Exception |
| `libxcursor1` | X cursor client library | MIT/X11 |
| `libxft2` | X FreeType interface library | MIT/X11 and component notices |
| `libxinerama1` | Xinerama client library | MIT/X11 |

APT also installs the dependencies of those packages. The exact base-image
and Debian package revisions depend on the image build date and target CPU
architecture. Their complete machine-readable notices are available inside a
built image under `/usr/share/doc/*/copyright`. They must be retained and
reviewed when redistributing the image.

## Optional deployment component

The Synology authentication guide provides an example using
[OAuth2 Proxy](https://github.com/oauth2-proxy/oauth2-proxy), which is MIT
licensed. OAuth2 Proxy is not built into the application image; it is a
separate optional service selected by the administrator.

## Checking a particular build

The most reliable license inventory is the one taken from the exact artifact
that will be distributed:

```console
docker compose build --pull
docker compose run --rm svg2stl-web python -m pip list
docker compose run --rm --entrypoint sh svg2stl-web \
  -c 'find /usr/share/doc -name copyright -type f -print'
```

For a formal release, record the base-image digest and resolved Python and
Debian versions alongside the artifact. Recheck licenses whenever dependency
ranges, the base image, or bundled browser files change.
