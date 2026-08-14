# Third-Party Notices

This project builds on the SVG parsing and mesh-generation approach introduced
by [MaxHalford/svg2stl](https://github.com/MaxHalford/svg2stl) and continued in
[avipars/svg2stl](https://github.com/avipars/svg2stl). That work is available
under the MIT License. Its original 2021 copyright notice is preserved in this
repository's `LICENSE` file.

Runtime and development dependencies are separate works governed by their own
licenses. In particular:

- [Gmsh](https://gmsh.info/) is distributed under the GNU General Public
  License, version 2 or later. The Python wheel used by this project includes
  the Gmsh application and SDK. Gmsh source and license information are
  available from its website and source repository.
- [FastAPI](https://github.com/fastapi/fastapi),
  [trimesh](https://github.com/mikedh/trimesh),
  [NumPy](https://github.com/numpy/numpy), and the remaining Python packages
  retain the licenses published with their distributions.
- [Three.js](https://github.com/mrdoob/three.js), version 0.185.1, is bundled
  for local STL rendering and is distributed under the MIT License. Its
  license text is retained in `app/static/THREE-LICENSE.txt`.
- The optional authentication example uses
  [OAuth2 Proxy](https://github.com/oauth2-proxy/oauth2-proxy), which is
  distributed under the MIT License.

The MIT License for this repository's source does not replace or alter any
third-party license. Review the dependency versions in `pyproject.toml` and the
licenses shipped in a built container image when preparing a redistribution.
