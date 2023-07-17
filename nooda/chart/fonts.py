import matplotlib.pyplot as plt
import os

from matplotlib import font_manager


def jakarta_sans():
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
