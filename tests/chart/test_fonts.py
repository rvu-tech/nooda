def test_jakarta_sans_sets_installed_flag():
    from nooda.chart import fonts

    fonts.HAS_BEEN_INSTALLED = False
    fonts.jakarta_sans()
    assert fonts.HAS_BEEN_INSTALLED is True
