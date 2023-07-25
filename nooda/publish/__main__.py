import marko
import nbformat
import sys

from argparse import ArgumentParser
from bs4 import BeautifulSoup
from collections import namedtuple
from os.path import dirname, join


def render_html(nb):
    html = ""

    with open(join(dirname(__file__), "base.html"), "r") as f:
        html += f.read()

    for cell in nb.cells:
        if "tags" in cell.metadata and "toc" in cell.metadata["tags"]:
            html += '<section id="toc"></section>'
        elif cell.cell_type == "markdown":
            html += f"<section>{marko.convert(cell.source)}</section>"
        elif cell.cell_type == "code":
            for output in cell.outputs:
                if "data" in output:
                    if "image/png" in output.data:
                        print(
                            {k: v for k, v in output.items() if k != "data"},
                            output.data.keys(),
                            file=sys.stderr,
                        )
                        print(output.data["text/plain"], file=sys.stderr)
                        html += f"<section class=\"bleed\"><img src=\"data:image/png;base64,{output.data['image/png']}\"></section>"
                    elif "text/markdown" in output.data:
                        html += f"<section>{marko.convert(output.data['text/markdown'])}</section>"
                    elif "text/html" in output.data:
                        html += f"<section>{output.data['text/html']}</section>"
                    elif "text/plain" in output.data:
                        if "application/vnd.jupyter.widget-view+json" in output.data:
                            print(
                                "probably a widget we don't want to show, not plain text output",
                                file=sys.stderr,
                            )
                            continue

                        html += (
                            f"<section><pre>{output.data['text/plain']}</pre></section>"
                        )

    return html


header_tags = ["h2", "h3", "h4", "h5", "h6"]


def header_level(header) -> int:
    return int(header.name[1:])


HeaderEntry = namedtuple("HeaderEntry", field_names=["id", "text", "elem", "children"])


def header_entries(soup) -> tuple[HeaderEntry, list[HeaderEntry]]:
    header_tree = HeaderEntry(id=None, text=None, elem=None, children=[])
    all_headers = []

    current_level = min(int(h[1:]) for h in header_tags)
    level_offset = current_level - 1
    current_ancestry = []
    current_entry = header_tree
    last_elem = None

    for h in soup.find_all(header_tags):
        level = header_level(h)

        if level > current_level:
            current_ancestry.append(current_entry)
            current_entry = last_elem
        elif level < current_level:
            current_entry = current_ancestry[level - level_offset - 1]
            current_ancestry = current_ancestry[: level - level_offset - 1]

        id = ".".join(
            [str(len(d.children)) for d in current_ancestry]
            + [str(len(current_entry.children) + 1)]
        )

        last_elem = HeaderEntry(id=id, text=h.text, elem=h, children=[])
        all_headers.append(last_elem)
        current_entry.children.append(last_elem)
        current_level = level

    return header_tree, all_headers


def render_header_entry(soup, entry):
    elem = soup.new_tag("ol")

    for child in entry.children:
        child_elem = soup.new_tag("li")
        link_elem = soup.new_tag("a", attrs={"href": f"#{child.id}"})
        link_elem.append(f"{child.id} {child.text}")
        child_elem.append(link_elem)
        if len(child.children) > 0:
            child_elem.append(render_header_entry(soup, child))

        elem.append(child_elem)

    return elem


def enrich_headers(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    header_tree, all_headers = header_entries(soup)

    for header in all_headers:
        header.elem.attrs["id"] = header.id
        header.elem.wrap(
            soup.new_tag("a", attrs={"href": f"#{header.id}", "class": "header"})
        )

    toc_elem = soup.find("section", id="toc")
    if not toc_elem is None:
        toc_elem.append(render_header_entry(soup, header_tree))

    return soup.prettify()


def publish(fd):
    nb = nbformat.read(fd, as_version=4)

    html = render_html(nb)
    html = enrich_headers(html)

    print(html)


def main():
    parser = ArgumentParser(prog="nooda.publish")

    parser.add_argument(
        "notebook",
        help="Notebook to process. If - will read from std in",
    )

    args = parser.parse_args()

    if args.notebook == "-":
        publish(sys.stdin)
    else:
        with open(args.notebook) as f:
            publish(f)


if __name__ == "__main__":
    main()
