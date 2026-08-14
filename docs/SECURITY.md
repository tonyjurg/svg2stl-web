# Security Policy

## Supported versions

Security fixes are applied to the current `main` branch. Published releases,
when available, state whether they include a security fix. Older commits and
locally modified deployments are not maintained separately.

## Artwork privacy

Keeping artwork local is a primary reason to self-host this application. The
browser sends an SVG only to the SVG to STL instance that the user opened. The
server processes it in a per-request temporary directory, returns the validated
STL directly to that browser, and deletes the working directory after the
response. The bundled STL preview also runs locally in the browser.

The application contains no cloud conversion integration, external analytics,
telemetry, advertising, or CDN-hosted runtime library. It does not intentionally
forward uploaded SVG or generated STL data to a third party.

This privacy boundary depends on the deployment. Run the service on a trusted
LAN when possible. If remote access is required, use HTTPS, authentication, and
firewall rules; keep the host and reverse proxy updated; and do not install
untrusted browser extensions or monitoring proxies that can read uploads. A
misconfigured, compromised, or publicly exposed host cannot provide the same
assurance as a properly secured local deployment.

## Dependency monitoring

Every push and pull request runs a blocking `pip-audit` job against the Python
runtime dependency tree. The check fails when the Python Packaging Advisory
Database reports a known vulnerability or when strict dependency collection
cannot complete.

Dependabot checks the Python requirements, GitHub Actions, and Docker base
image every week and proposes updates as pull requests. `pip-audit` covers
Python packages only; it does not replace review of Debian packages, bundled
native libraries, container scanners, or newly disclosed issues that are not
yet present in an advisory database.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private SVG
files, NAS addresses, or authentication logs.

Use GitHub's **Security > Report a vulnerability** form for this repository.
If private vulnerability reporting is not available, open a minimal issue that
asks the maintainer for a private contact channel without disclosing technical
details.

Include, when relevant:

- the affected commit or release;
- deployment method and architecture;
- a concise description of the impact;
- reproducible steps using non-sensitive data;
- whether authentication can be bypassed;
- suggested remediation, if known.

Reports will be acknowledged as time permits. Please allow a reasonable period
for investigation and remediation before public disclosure.

## Deployment responsibility

The application has no built-in accounts. Operators are responsible for
network restrictions, HTTPS, authentication, updates, and preventing direct
access that bypasses an authentication proxy. See
[DSM user authentication](docs/AUTHENTICATION.md) and
[deployment security](docs/DEPLOYMENT.md#network-and-access).
