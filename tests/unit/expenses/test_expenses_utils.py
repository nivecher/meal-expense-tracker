"""Tests for expense utility functions."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from werkzeug.datastructures import FileStorage

from app.expenses.utils import save_receipt


class TestSaveReceipt:
    """Test the save_receipt utility function."""

    def test_save_receipt_success_pdf(self):
        """Test saving a PDF receipt successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock file storage
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.pdf"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            # Verify the file was saved
            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.pdf")
            assert result.startswith("20")  # timestamp format YYYYMMDD

    def test_save_receipt_success_jpg(self):
        """Test saving a JPG receipt successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.JPG"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.jpg")  # extension normalized to lowercase

    def test_save_receipt_success_jpeg(self):
        """Test saving a JPEG receipt successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.jpeg"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.jpeg")

    def test_save_receipt_success_png(self):
        """Test saving a PNG receipt successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.png"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.png")

    def test_save_receipt_success_gif(self):
        """Test saving a GIF receipt successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.gif"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.gif")

    def test_save_receipt_no_filename(self):
        """Test saving a file with no filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = None
            mock_file.save = Mock()

            # This should raise an error because "receipt" has no extension
            with pytest.raises(ValueError, match="File type not allowed"):
                save_receipt(mock_file, temp_dir)

    def test_save_receipt_empty_filename(self):
        """Test saving a file with empty filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = ""
            mock_file.save = Mock()

            # This should raise an error because "receipt" has no extension
            with pytest.raises(ValueError, match="File type not allowed"):
                save_receipt(mock_file, temp_dir)

    def test_save_receipt_invalid_extension(self):
        """Test saving a file with invalid extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.txt"

            with pytest.raises(ValueError, match="File type not allowed"):
                save_receipt(mock_file, temp_dir)

    def test_save_receipt_no_extension(self):
        """Test saving a file with no extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt"

            with pytest.raises(ValueError, match="File type not allowed"):
                save_receipt(mock_file, temp_dir)

    def test_save_receipt_creates_directory(self):
        """Test that the function creates the upload directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = os.path.join(temp_dir, "nonexistent", "subdir")

            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.pdf"
            mock_file.save = Mock()

            save_receipt(mock_file, upload_dir)

            # Verify directory was created
            assert os.path.exists(upload_dir)
            mock_file.save.assert_called_once()

    @patch("os.makedirs")
    def test_save_receipt_os_error(self, mock_makedirs):
        """Test handling of OSError when creating directories."""
        mock_makedirs.side_effect = OSError("Permission denied")

        mock_file = Mock(spec=FileStorage)
        mock_file.filename = "receipt.pdf"

        with pytest.raises(OSError, match="Permission denied"):
            save_receipt(mock_file, "/invalid/path")

    def test_save_receipt_filename_with_spaces(self):
        """Test saving a file with spaces in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "my receipt file.pdf"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_my receipt file.pdf")

    def test_save_receipt_filename_with_special_chars(self):
        """Test saving a file with special characters in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt_2024-01-01@12:00.pdf"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt_2024-01-01@12:00.pdf")

    def test_save_receipt_timestamp_format(self):
        """Test that the timestamp is in the correct format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.pdf"
            mock_file.save = Mock()

            with patch("app.expenses.utils.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.strftime.return_value = "20240101_120000"
                mock_datetime.now.return_value = mock_now

                result = save_receipt(mock_file, temp_dir)

                assert result == "20240101_120000_receipt.pdf"

    def test_save_receipt_multiple_extensions(self):
        """Test saving files with multiple dots in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.backup.pdf"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.backup.pdf")

    def test_save_receipt_case_insensitive_extension(self):
        """Test that file extension validation is case insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Mock(spec=FileStorage)
            mock_file.filename = "receipt.PDF"
            mock_file.save = Mock()

            result = save_receipt(mock_file, temp_dir)

            mock_file.save.assert_called_once()
            assert result.endswith("_receipt.pdf")  # lowercase extension
