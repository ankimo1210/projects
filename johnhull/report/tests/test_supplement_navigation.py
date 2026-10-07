"""Accepted chapter lessons must be discoverable from the normal portal entrance."""

from html.parser import HTMLParser

from report_builder.render import render_site


class ChapterLinks(HTMLParser):
    """Collect actual links to the separately built chapter lessons."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("chapters/"):
                self.links.append(href)


def test_normal_entrance_lists_every_supplement_and_its_network_requirement(tmp_path):
    """The homepage must expose all 34 accepted chapter companions once each."""
    output = render_site(output_dir=tmp_path, log=lambda *_args: None)
    text = (output / "index.html").read_text()
    parser = ChapterLinks()
    parser.feed(text)
    expected = {f"chapters/ch{chapter:02d}.html" for chapter in (*range(1, 26), *range(29, 38))}
    assert set(parser.links) == expected
    assert len(parser.links) == len(expected)
    assert "数式表示にはインターネット接続が必要" in text
