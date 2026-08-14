from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


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
    for guide in ("USAGE", "DEPLOYMENT", "TROUBLESHOOTING", "API", "DEVELOPMENT"):
        assert f"docs/{guide}.md" in page
    assert "/blob/main/SECURITY.md" in page


def test_pages_site_has_valid_local_references_and_fragments() -> None:
    parser = parse_page()
    assert len(parser.ids) == len(set(parser.ids))

    for reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            assert (SITE / parsed.path).is_file(), reference
        if parsed.fragment:
            assert parsed.fragment in parser.ids, reference


def test_pages_site_includes_both_animated_outputs_and_reduced_motion() -> None:
    page = (SITE / "index.html").read_text(encoding="utf-8")
    styles = (SITE / "styles.css").read_text(encoding="utf-8")

    assert "Create precise stencils from your SVG artwork" in page
    assert "Stencil is the main event" in page
    assert "Design stencil bridges" in page
    assert 'class="form-animation"' in page
    assert 'class="stencil-animation"' in page
    assert 'id="motion-toggle"' in page
    assert "@keyframes form-rise" in styles
    assert "@keyframes cutter-drop" in styles
    assert "@keyframes stencil-lift" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


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
        and step.get("with", {}).get("path") == "site"
        for step in steps
    )
    assert any(step.get("uses") == "actions/deploy-pages@v4" for step in steps)
