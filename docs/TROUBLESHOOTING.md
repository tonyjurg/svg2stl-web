# Troubleshooting

## The page does not open

Confirm the service is running:

```bash
docker compose ps
docker compose logs --tail 100 svg2stl-web
curl http://localhost:8080/api/health
```

On a NAS, replace `localhost` with the NAS address when testing from another
computer. Check that the DSM firewall permits the chosen host port from your
local subnet.

If port 8080 is already occupied, change the host side of the mapping in
`compose.yaml`, for example from `8080:8080` to `8090:8080`.

## No path drawing data was found

The SVG contains no `<path>` element with a non-empty `d` attribute. Text,
circles, rectangles, and other primitives may be visible but are not paths.

Convert the artwork to paths in the SVG editor, save the result, and upload it
again. See [Preparing an SVG](USAGE.md#preparing-an-svg).

## No usable closed SVG contours were found

The file has path data, but none of its contours contains an explicit SVG close
command (`Z` or `z`). Close the paths in the editor. Merely placing the last
point on top of the first is not sufficient for the current parser.

## The output does not match the SVG preview

The browser preview uses the browser's full SVG renderer; the converter handles
only closed path geometry. The usual causes are:

- text or primitive elements were not converted to paths;
- transforms were not applied to path coordinates;
- the visual result depends on strokes, fill rules, masks, or clipping;
- nested or overlapping contours were used;
- hidden paths remain in the document.

Flatten the document to simple, independent, closed paths. A plain SVG export
from the editor is usually easier to diagnose than an editor-specific SVG.

## The stencil has the wrong openings

Stencil mode treats every closed path as a hole in one rectangular surface. It
does not infer that one contour is inside another. Nested artwork, including
letters with counters, needs to be simplified into supported independent
cutouts or redesigned with stencil bridges.

## Solid shape mode produces separate pieces

Each closed path becomes its own extruded solid. This is expected. Join paths
in the SVG editor when the parts should be one connected object, or arrange and
manage the parts separately in the slicer.

## Curves look faceted

Increase **Curve detail** gradually. A higher setting samples every curve and
arc more often. It also creates more triangles and takes longer to convert.
Avoid using the maximum until a lower value has been checked in the slicer.

## Conversion times out

First reduce curve detail and remove duplicate or unnecessary paths. If a
legitimate complex file still needs more time, increase
`CONVERSION_TIMEOUT_SECONDS` in `compose.yaml` and rebuild the project.

Also inspect container memory use. The supplied limit is 1 GB. Raising the
timeout will not help when the worker is being terminated for exceeding the
memory limit.

## Conversion failed without a useful explanation

If the web interface reports `Conversion failed before a valid STL could be
produced`, temporarily enable runtime diagnostics in `compose.yaml`:

```yaml
environment:
  DIAGNOSTIC_ERRORS: "true"
```

Recreate the project in Container Manager; rebuilding the image is unnecessary.
Retry the conversion and the web interface will report the worker's exit status
or termination signal plus a bounded, path-sanitized diagnostic excerpt. For
example, `SIGKILL` can indicate an out-of-memory kill, `SIGSEGV` a native crash,
and `SIGILL` an unsupported CPU instruction. Set the option back to `"false"`
after troubleshooting, especially if untrusted users can access the service.

## Container image fails to build on Synology

Check the NAS processor architecture. The supplied image targets x86-64. ARM
models generally cannot install the required Gmsh Python wheel without a custom
build.

For x86-64 models, inspect the build log in Container Manager. Network or DNS
errors during `apt-get` or `pip install` usually indicate that the NAS cannot
reach Debian or Python package repositories.

If container creation fails with `NanoCPUs can not be set` or reports that the
kernel does not support the CPU CFS scheduler, remove any `cpus` setting from
the Container Manager project and recreate it. The supplied `compose.yaml`
omits this setting for compatibility with these kernels.

## The STL still looks wrong in a slicer

The server will only return a mesh that is watertight, consistently wound, a
positive volume, manifold, and free from degenerate or duplicate faces. If the
slicer display is still surprising:

1. Confirm the selected output mode.
2. Compare the result dimensions with the requested dimensions.
3. Check whether shape mode contains several disconnected pieces.
4. Reopen the STL in a second viewer or slicer.
5. Test with `examples/simple_shapes.svg` to separate an input problem from an
   installation problem.

Validation establishes mesh topology; it does not establish printability of
thin features, bridges, clearances, or unsupported geometry.

## Collecting useful diagnostics

When reporting a problem, include:

- the application commit from `git rev-parse --short HEAD`;
- whether it runs locally or in Docker;
- host and NAS architecture;
- selected output mode and settings;
- the exact error shown in the browser;
- the relevant container log lines;
- a small non-sensitive SVG that reproduces the issue.

Do not attach private artwork unless it is necessary and safe to share.

