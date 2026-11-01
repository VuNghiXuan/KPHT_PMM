from django.core.exceptions import ValidationError

MAX_FILE_SIZE_MB = 10  # Giới hạn 10MB để đảm bảo hiệu năng Ollama

def validate_file_size(file_obj):
    megabyte_limit = MAX_FILE_SIZE_MB
    if file_obj.size > megabyte_limit * 1024 * 1024:
        raise ValidationError(
            f"Dung lượng file vượt quá giới hạn cho phép ({megabyte_limit}MB). Vui lòng chọn file nhỏ hơn."
        )