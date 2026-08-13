# Contributing

Contributions are welcome, especially small reproducible SVG cases, mesh
validation improvements, documentation corrections, and support for additional
well-defined SVG geometry.

## Before opening an issue

1. Check the [supported SVG behavior](docs/USAGE.md#supported-path-data).
2. Search existing issues for the same error or requested feature.
3. Reproduce the problem with the latest `main` branch.
4. Reduce the input to the smallest non-sensitive SVG that still fails.

Do not publish private artwork, credentials, NAS addresses, logs containing
tokens, or authentication configuration. Follow [SECURITY.md](SECURITY.md) for
security vulnerabilities.

## Development setup

Follow the [development guide](docs/DEVELOPMENT.md#local-setup), then run:

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m pip check
```

Geometry tests perform real Gmsh conversions and can take longer than ordinary
unit tests.

## Pull requests

- Keep each pull request focused on one behavior or closely related set of
  changes.
- Add a regression test for every converter or API behavior change.
- Confirm generated meshes remain watertight, consistently wound, manifold,
  non-degenerate, duplicate-free, and positive-volume.
- Update the UI, API, worker, tests, and documentation together when adding a
  conversion setting.
- Use neutral example artwork that can be redistributed under this project's
  license.
- Explain user-visible behavior and limitations in the pull request body.

Do not weaken mesh validation to make a new geometry case pass. Fix the
geometry construction or document the unsupported case instead.

## Style

Use the existing structure and straightforward comments that explain why a
non-obvious geometry or security decision exists. Python formatting and linting
are enforced by Ruff. Keep documentation examples generic and free of personal
hostnames, addresses, or secrets.

By contributing, you agree that your contribution may be distributed under the
repository's [MIT License](LICENSE).

## AI-assisted contributions

AI-assisted contributions are welcome when the contributor understands,
reviews, and takes responsibility for the submitted work. Disclose material AI
assistance in the pull request and describe the tests or manual checks used to
verify it. Do not submit generated code, documentation, or test cases that you
cannot explain or maintain.

See the project's [AI-assisted development disclosure](AI_ASSISTED_DEVELOPMENT.md)
for the transparency standard used for the initial application.
