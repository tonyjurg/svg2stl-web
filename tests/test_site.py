from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        reference_attribute = {
            "a": "href",
            "img": "src",
            "link": "href",
            "script": "src",
        }.get(tag)
        if reference_attribute and (reference := attributes.get(reference_attribute)):
            self.references.append(reference)


def parse_page() -> PageParser:
    parser = PageParser()
    parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
    return parser


def test_pages_site_links_to_every_detailed_guide() -> None:
    page = (SITE / "index.html").read_text(encoding="utf-8")
    for guide in (
        "usage",
        "deployment",
        "authentication",
        "troubleshooting",
        "api",
        "development",
        "security",
    ):
        assert f"manual.html?guide={guide}" in page


def test_pages_site_has_valid_local_references_and_fragments() -> None:
    parser = parse_page()
    assert len(parser.ids) == len(set(parser.ids))

    for reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            assert (SITE / parsed.path).is_file(), reference
        if parsed.fragment and not parsed.path:
            assert parsed.fragment in parser.ids, reference


def test_pages_site_uses_real_screenshots_and_reduced_motion() -> None:
    page = (SITE / "index.html").read_text(encoding="utf-8")
    styles = (SITE / "styles.css").read_text(encoding="utf-8")

    assert "Create precise stencils from your SVG artwork" in page
    assert "Stencil is the main event" in page
    assert "Design stencil bridges" in page
    for screenshot in (
        "app-source.png",
        "app-stencil-result.png",
        "app-solid-result.png",
    ):
        assert f"assets/{screenshot}" in page
        assert (SITE / "assets" / screenshot).is_file()
    assert 'id="motion-toggle"' in page
    assert "@keyframes screenshot-drift" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


def test_integrated_manual_can_load_every_markdown_guide() -> None:
    manual = (SITE / "manual.html").read_text(encoding="utf-8")
    script = (SITE / "manual.js").read_text(encoding="utf-8")
    for filename in (
        "USAGE.md",
        "DEPLOYMENT.md",
        "AUTHENTICATION.md",
        "TROUBLESHOOTING.md",
        "API.md",
        "DEVELOPMENT.md",
        "SECURITY.md",
    ):
        assert filename in script
        assert (SITE / filename).is_file()
    assert 'id="manual-article"' in manual
    assert (SITE / "SECURITY.md").read_text(encoding="utf-8") == (
        ROOT / "SECURITY.md"
    ).read_text(encoding="utf-8")


def test_pages_workflow_deploys_only_the_static_site() -> None:
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert workflow["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    steps = workflow["jobs"]["deploy"]["steps"]
    assert any(step.get("uses") == "actions/configure-pages@v5" for step in steps)
    assert any(
        step.get("uses") == "actions/upload-pages-artifact@v4"
        and step.get("with", {}).get("path") == "docs"
        for step in steps
    )
    assert any(step.get("uses") == "actions/deploy-pages@v4" for step in steps)
