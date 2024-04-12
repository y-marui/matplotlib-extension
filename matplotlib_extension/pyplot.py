import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import dill
import fitz
from send2trash import send2trash
from pypdf import PdfWriter
from pathlib import Path

def savefig(fig:plt.figure, filename:Path, mode: str = "x"):
    """Save the current figure to a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to save the figure to.
    """
    assert mode in ["x", "w", "a"]

    if isinstance(filename, str):
        filename = Path(filename) 
        
    with PdfWriter() as merger:   
        if isinstance(filename, Path) and filename.exists():
            if mode == "x":
                raise FileExistsError(f"{filename}")
            elif mode == "w":
                send2trash(filename)
            elif mode == "a":
                merger.append(filename)

        with BytesIO() as fp_pdf:
            fig.savefig(fp_pdf, format="pdf")
            fp_pdf.seek(0)
    
            with BytesIO() as fp_dill:
                dill.dump(fig, fp_dill)
                fp_dill.seek(0)
    
                doc = fitz.open("pdf", fp_pdf) 
                page = doc[0]
                page.add_file_annot(None, fp_dill, "fig.dill")
                doc.save(fp_pdf)
                fp_pdf.seek(0)

            merger.append(fp_pdf)

        merger.write(filename)


def loadfig(filename:str)->plt.figure:
    """Load the figure from a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to load the figure from.

    Returns:
        plt.figure: The figure object.
    """
    if isinstance(filename, str):
        filename = Path(filename) 
        
    with filename.open("rb") as fp:
        doc = fitz.open(fp)
        figs = []
        for page in doc:
            for annot in page.annots():
                if annot.info["content"] == 'fig.dill':
                    fig = dill.loads(annot.get_file())
                    figs.append(fig)
                    break
            
        return figs