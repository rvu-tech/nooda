from .send import send


def load_ipython_extension(ipython):
    """Called by IPython when this module is loaded as an IPython extension."""
    from nooda.slack.magic import _line_magic

    ipython.register_magic_function(_line_magic, magic_kind="line", magic_name="slack")
