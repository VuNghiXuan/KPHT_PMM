import os
import torch
import logging

logger = logging.getLogger(__name__)

class PipelineManager:
    @staticmethod
    def configure_environment():
        """
        Tự động cấu hình môi trường dựa trên khả năng phần cứng của Server.
        Phải được gọi trước khi import các thư viện nặng như docling, transformers.
        """
        # 1. Kiểm tra khả năng hỗ trợ CUDA
        if not torch.cuda.is_available():
            logger.warning("[System] CUDA không khả dụng, cấu hình tối ưu cho CPU...")
            os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        
        # 2. Vô hiệu hóa JIT Compile nếu không có trình biên dịch C++
        # Tránh lỗi 'cl.exe' trên Windows hoặc thiếu build-essential trên Linux
        if os.name == 'nt':  # Chỉ áp dụng mạnh trên Windows
            os.environ["TORCH_COMPILE_DISABLE"] = "1"
            os.environ["TORCH_DYNAMO_DISABLE"] = "1"
            
        # 3. Tắt cảnh báo Symlink cho HuggingFace
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        
        logger.info("[System] Pipeline environment configured successfully.")

# Gọi cấu hình ngay khi module được load hoặc tại entry point của App
PipelineManager.configure_environment()