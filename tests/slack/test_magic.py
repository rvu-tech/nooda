def test_magic_module_imports_without_error():
    """Importing magic.py should not crash on a missing module."""
    from nooda.slack import magic

    assert hasattr(magic, "_slack_line_magic")
