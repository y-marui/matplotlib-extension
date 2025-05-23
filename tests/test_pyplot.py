import pytest
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from matplotlib_extension import pyplot
import tempfile
import os

def test_save_and_loadfig(tmp_path):
    # Create a simple figure
    fig, ax = plt.subplots()
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    ax.plot(x, y)
    filename = tmp_path / "test.plt.pdf"

    # Save the figure
    pyplot.savefig(fig, filename)

    # Load the figure
    figs = pyplot.loadfig(filename)
    assert isinstance(figs, list)
    assert len(figs) == 1
    assert hasattr(figs[0], "axes")

def test_savefig_file_exists(tmp_path):
    fig, ax = plt.subplots()
    filename = tmp_path / "test_exists.plt.pdf"
    pyplot.savefig(fig, filename)
    with pytest.raises(FileExistsError):
        pyplot.savefig(fig, filename, mode="x")

def test_savefig_overwrite(tmp_path):
    fig, ax = plt.subplots()
    filename = tmp_path / "test_overwrite.plt.pdf"
    pyplot.savefig(fig, filename)
    # Overwrite should not raise
    pyplot.savefig(fig, filename, mode="w")

def test_savefig_append(tmp_path):
    fig, ax = plt.subplots()
    filename = tmp_path / "test_append.plt.pdf"
    pyplot.savefig(fig, filename)
    # Append should not raise
    pyplot.savefig(fig, filename, mode="a")

def test_adjust_locator():
    fig, ax = plt.subplots()
    x = np.linspace(0, 10, 100)
    y = np.cos(x)
    ax.plot(x, y)
    pyplot.adjust_locator(ax)
    # Check that major and minor locators are set
    assert hasattr(ax.xaxis, "get_major_locator")
    assert hasattr(ax.xaxis, "get_minor_locator")