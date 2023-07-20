from .send import send


def load_ipython_extension(ipython):
    """Called by IPython when this module is loaded as an IPython extension."""
    from nooda.slack.magic import _slack_line_magic, _slack_thread_line_magic

    ipython.register_magic_function(
        _slack_line_magic, magic_kind="line", magic_name="slack"
    )
    ipython.register_magic_function(
        _slack_thread_line_magic, magic_kind="line", magic_name="slack_thread"
    )
