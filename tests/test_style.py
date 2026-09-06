import matplotlib.pyplot as plt


def test_article_small_matches_combined_style():
    with plt.style.context(
        ["matplotlib_extension.article", "matplotlib_extension.small"]
    ):
        combined = dict(plt.rcParams)

    with plt.style.context("matplotlib_extension.article_small"):
        single = dict(plt.rcParams)

    assert single == combined
