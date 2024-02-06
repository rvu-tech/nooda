import matplotlib.pyplot as plt
import os

from matplotlib import font_manager

HAS_BEEN_INSTALLED = False


def jakarta_sans():
    if HAS_BEEN_INSTALLED:
        return

    font_dir = [
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "fonts", "Plus_Jakarta_Sans"
        )
    ]
    for font in font_manager.findSystemFonts(font_dir):
        font_manager.fontManager.addfont(font)

    plt.rcParams.update(
        {
            "font.family": "Plus Jakarta Sans",
        }
    )


jakarta_sans()
