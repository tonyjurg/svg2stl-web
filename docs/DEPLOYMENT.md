# Deployment

The supplied image runs one FastAPI web worker. Each conversion is performed
in a short-lived child process, and one conversion is admitted at a time by
default. This is a conservative configuration for a small NAS.

## Requirements

- An x86-64 Docker host
- Docker Engine with Docker Compose, or Synology Container Manager
- Approximately 1 GB RAM available during conversion
- Port 8080 available, unless the Compose port mapping is changed

The image is built from `python:3.13-slim-bookworm` and installs the Gmsh wheel
plus its small Linux runtime libraries. The standard Gmsh Python package used
here does not provide a normal Linux ARM wheel, so ARM Synology models need a
different image or a locally compiled Gmsh installation.

## Docker Compose

Start the service from the repository root:

```bash
docker compose up --build -d
docker compose ps
```

Check its health:

```bash
curl http://localhost:8080/api/health
```

View logs:

```bash
docker compose logs --follow svg2stl-web
```

Stop the service without removing its image:

```bash
docker compose down
```

## Synology Container Manager

### Copy the project to the NAS

Clone the repository on the NAS or another computer and copy the complete
folder to a shared NAS folder:

```bash
git clone https://github.com/tonyjurg/svg2stl-web.git
```

You can also download a source archive from the repository's Releases or Code
menu and unpack it on the NAS.

A suitable project path is `/volume1/docker/svg2stl-web`.

### Create the project

1. Open **Container Manager** in DSM.
2. Open **Project** and select **Create**.
3. Enter `svg2stl-web` as the project name.
4. Select the folder containing this repository as the project path.
5. Use the existing `compose.yaml` as the Compose configuration.
6. Review the settings, build the image, and start the project.
7. Open `http://NAS-IP:8080` from another computer on the same network.

Synology documents the Project workflow in its
[Container Manager Project guide](https://kb.synology.com/en-us/DSM/help/ContainerManager/docker_project).

## Configuration

Edit the environment values in `compose.yaml` before recreating the service:

| Variable | Default | Description |
| --- | ---: | --- |
| `MAX_UPLOAD_BYTES` | `5242880` | Maximum uploaded SVG size in bytes |
| `CONVERSION_TIMEOUT_SECONDS` | `180` | Maximum duration of a conversion process |
| `MAX_CONCURRENT_CONVERSIONS` | `1` | Number of simultaneous conversion jobs |
| `DIAGNOSTIC_ERRORS` | `false` | Show bounded worker exit diagnostics in conversion errors |

Set `DIAGNOSTIC_ERRORS` to `"true"` temporarily when a conversion fails with
no useful explanation. Recreate the container after changing the value; an
image rebuild is not required. Diagnostic mode identifies signals such as
`SIGKILL`, `SIGSEGV`, and `SIGILL`, includes a bounded tail of worker output,
and removes container filesystem paths. Disable it again after troubleshooting,
particularly when the service is reachable outside a trusted network.

The Compose file also limits the container to 1 GB RAM, 128 processes, and
256 MB of temporary storage. It intentionally does not set a CPU quota because
some NAS kernels, including some Synology releases, do not support Docker's CPU
CFS quota. Increase the memory or temporary-storage limit only when legitimate
complex SVG files consistently exceed it.

To publish a different host port, change only the first number:

```yaml
ports:
  - "8090:8080"
```

The application would then be available at `http://NAS-IP:8090`.

## Storage and backups

The application has no database and no persistent application data. SVG and
STL files live under the container's temporary filesystem and are deleted after
the download response. There is therefore no application-data volume to back
up.

Back up the repository or keep it in GitHub. User uploads are intentionally not
recoverable.

## Updating

From a shell checkout:

```bash
git pull --ff-only
docker compose up --build -d
```

In Container Manager, update the repository folder, select the project, choose
**Action > Build**, and then start or restart it. A rebuild is required when
Python code or dependencies change.

## Network and access

The application has no authentication. Do not expose port 8080 directly to the
public internet.

For LAN-only use:

- allow port 8080 only from trusted private subnets in the NAS firewall;
- avoid router port forwarding;
- use a fixed NAS address or local DNS name.

For access through a friendly HTTPS name, configure a DSM reverse proxy whose
destination is `http://127.0.0.1:8080`. Apply an access-control profile or an
authentication layer appropriate for your network. Synology's current DSM 7
path is **Control Panel > Login Portal > Advanced > Reverse Proxy**; see the
[official reverse proxy guide](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/system_login_portal_advanced?version=7).

A DSM reverse-proxy rule does not by itself require a DSM username and
password. To protect the application with Synology user accounts, follow the
[DSM user authentication guide](AUTHENTICATION.md). That setup exposes an OIDC
authentication proxy instead of exposing this application directly.

The container itself provides these protections:

- non-root user `10001`;
- read-only root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- bounded in-memory temporary storage;
- upload size and conversion time limits;
- XML external entities disabled;
- controlled client-facing errors;
- browser security headers.

These controls reduce risk but do not replace authentication for an
internet-facing service.
