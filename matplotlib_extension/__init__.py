__version__ = "0.1.0"

from matplotlib_extension.package import PackageError, UnsupportedFigureWarning
from matplotlib_extension.pyplot import install_matplotlib_savefig, loadfig, recover_data, savefig

install_matplotlib_savefig()

__all__ = [
    "PackageError",
    "UnsupportedFigureWarning",
    "install_matplotlib_savefig",
    "loadfig",
    "recover_data",
    "savefig",
]
