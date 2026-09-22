from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import MagicMock
from apps.group_chat.validators import validate_file_size

class TestFileValidation(TestCase):
    """Kiểm thử tính năng giới hạn dung lượng file upload (<= 10MB)"""

    def test_file_size_within_limit(self):
        """File <= 10MB phải hợp lệ"""
        mock_file = MagicMock()
        mock_file.size = 5 * 1024 * 1024  # 5MB
        
        try:
            validate_file_size(mock_file)
        except ValidationError:
            self.fail("validate_file_size đã ném ValidationError đối với file 5MB hợp lệ!")

    def test_file_size_exceeds_limit(self):
        """File > 10MB phải ném ra ValidationError"""
        mock_file = MagicMock()
        mock_file.size = 11 * 1024 * 1024  # 11MB
        
        with self.assertRaises(ValidationError):
            validate_file_size(mock_file)