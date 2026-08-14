# Security Policy

## Supported versions

Security fixes are applied to the current `main` branch. Published releases,
when available, state whether they include a security fix. Older commits and
locally modified deployments are not maintained separately.

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
