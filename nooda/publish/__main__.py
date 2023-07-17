import marko
import nbformat
import sys

from argparse import ArgumentParser
from os.path import dirname, join


def publish(filename):
    nb_dir = dirname(filename)

    with open(filename) as f:
        nb = nbformat.read(f, as_version=4)

    with open(join(dirname(__file__), "base.html"), "r") as f:
        print(f.read())

    for cell in nb.cells:
        if cell.cell_type == "markdown":
            print(f"<section>{marko.convert(cell.source)}</section>")
        elif cell.cell_type == "code":
            for output in cell.outputs:
                if output.output_type == "display_data":
                    if "image/png" in output.data:
                        print(
                            {k: v for k, v in output.items() if k != "data"},
                            output.data.keys(),
                            file=sys.stderr,
                        )
                        print(output.data["text/plain"], file=sys.stderr)
                        print(
                            f"<section class=\"bleed\"><img src=\"data:image/png;base64,{output.data['image/png']}\"></section>"
                        )
                    elif "text/plain" in output.data:
                        if "application/vnd.jupyter.widget-view+json" in output.data:
                            print(
                                "probably a widget we don't want to show, not plain text output",
                                file=sys.stderr,
                            )
                            continue

                        print(
                            f"<section><pre>{output.data['text/plain']}</pre></section>"
                        )


def main():
    parser = ArgumentParser(prog="nooda.publish")

    parser.add_argument(
        "notebook",
        help="Notebook to process",
    )

    args = parser.parse_args()

    print()

    publish(args.notebook)


if __name__ == "__main__":
    main()
