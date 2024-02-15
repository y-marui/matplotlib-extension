import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import dill
import fitz

def savefig(fig:plt.figure, filename:str):
    """Save the current figure to a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to save the figure to.
    """
    with BytesIO() as fp_pdf:
        fig.savefig(fp_pdf, format="pdf")
        fp_pdf.seek(0)

        with BytesIO() as fp_dill:
            dill.dump(fig, fp_dill)
            fp_dill.seek(0)

            doc = fitz.open("pdf", fp_pdf) 
            
            page = doc[0]
            
            file_annotation = page.add_file_annot(None, fp_dill, "fig.dill")
            
            doc.save(filename)


def loadfig(filename:str)->plt.figure:
    """Load the figure from a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to load the figure from.

    Returns:
        plt.figure: The figure object.
    """
    with open(filename, "rb") as fp:
        doc = fitz.open(fp)
        page = doc[0]
        annot = page.first_annot
        fig = dill.load(annot.file)
        return fig