# HTTP API

The browser interface uses a small HTTP API that can also be called from
scripts. Interactive OpenAPI and ReDoc pages are disabled to keep the deployed
service surface small.

## Health check

```http
GET /api/health
```

Successful response:

```json
{"status":"ok"}
```

## Convert an SVG

```http
POST /api/convert
Content-Type: multipart/form-data
```

### Form fields

| Field | Type | Required | Default | Allowed values |
| --- | --- | --- | ---: | --- |
| `svg` | file | Yes | - | Non-empty filename ending in `.svg` |
| `output_mode` | string | No | `stencil` | `stencil`, `shape` |
| `height_mm` | number | No | `80` | 5-1000 |
| `thickness_mm` | number | No | `3` | 0.4-50 |
| `border_mm` | number | No | `10` | 0-200; ignored in shape mode |
| `definition` | integer | No | `12` | 3-48 |

### curl example

```bash
curl --fail-with-body \
  --output simple_shapes_shape.stl \
  --form "svg=@examples/simple_shapes.svg;type=image/svg+xml" \
  --form "output_mode=shape" \
  --form "height_mm=80" \
  --form "thickness_mm=3" \
  --form "border_mm=10" \
  --form "definition=12" \
  http://localhost:8080/api/convert
```

On success, the response body is a binary STL with media type `model/stl`.
The download filename ends in `_stencil.stl` or `_shape.stl`.

### Validation headers

| Header | Meaning |
| --- | --- |
| `X-Output-Mode` | `stencil` or `shape` |
| `X-Mesh-Vertices` | Number of merged mesh vertices |
| `X-Mesh-Faces` | Number of triangular faces |
| `X-Mesh-Width` | X extent in millimetres |
| `X-Mesh-Height` | Y extent in millimetres |
| `X-Mesh-Thickness` | Z extent in millimetres |
| `X-Mesh-Watertight` | `true` when the mesh is watertight |
| `X-Mesh-Winding` | `true` when face winding is consistent |
| `Cache-Control` | `no-store` |

The server does not return an STL if its complete validation contract fails.

## Errors

API errors use FastAPI's JSON shape:

```json
{"detail":"No usable closed SVG contours were found"}
```

| Status | Typical reason |
| ---: | --- |
| 400 | Empty file, invalid XML, wrong XML root, or no path data |
| 413 | Upload exceeds `MAX_UPLOAD_BYTES` |
| 415 | Filename does not end in `.svg` |
| 422 | Invalid form values or conversion/mesh failure |
| 504 | Conversion exceeded `CONVERSION_TIMEOUT_SECONDS` |
| 500 | Unexpected worker or server failure |

Error details are deliberately controlled and do not include the worker command
or server filesystem paths. When the runtime variable `DIAGNOSTIC_ERRORS` is
`true`, abnormal worker exits include the exit status or signal and a bounded,
path-sanitized tail of worker output. This mode is intended for temporary
troubleshooting and is disabled by default.

## Concurrency and cleanup

Requests may wait for a conversion slot. The default is one active conversion
at a time. Each accepted upload receives its own temporary directory and Gmsh
worker process. The directory is removed after the response completes or as
soon as an error is handled.
