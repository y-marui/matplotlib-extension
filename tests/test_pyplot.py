from matplotlib_extension.pyplot import savefig

def test_savefig():
    pass

# import unittest
# from unittest.mock import patch, mock_open
# from matplotlib_extension.pyplot import savefig
# import fitz
# import dill
# import matplotlib.pyplot as plt
# from io import BytesIO

# class TestSaveFig(unittest.TestCase):
#     @patch("matplotlib.pyplot.savefig")
#     @patch("dill.dump")
#     @patch("fitz.open")
#     def test_savefig(self, mock_fitz_open, mock_dill_dump, mock_plt_savefig):
#         # モックオブジェクトを作成
#         mock_doc = mock_fitz_open.return_value
#         mock_page = mock_doc.__getitem__.return_value
#         mock_file_annot = mock_page.add_file_annot

#         # テスト対象の関数を呼び出す
#         savefig("test_filename")

#         # matplotlib.pyplot.savefigが正しく呼び出されたことを確認
#         mock_plt_savefig.assert_called_once_with(mock.ANY, format="pdf")

#         # dill.dumpが正しく呼び出されたことを確認
#         mock_dill_dump.assert_called_once_with(mock.ANY, mock.ANY)

#         # fitz.openが正しく呼び出されたことを確認
#         mock_fitz_open.assert_called_once_with("pdf", mock.ANY)

#         # add_file_annotが正しく呼び出されたことを確認
#         mock_file_annot.assert_called_once_with(None, mock.ANY, "fig.dill")

#         # doc.saveが正しく呼び出されたことを確認
#         mock_doc.save.assert_called_once_with("test_filename")

# if __name__ == "__main__":
#     unittest.main()