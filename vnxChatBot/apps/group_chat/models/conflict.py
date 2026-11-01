"""
File: apps/group_chat/models/conflict.py
Mục đích: Quản lý nhật ký xung đột và vòng đời giải quyết mâu thuẫn tri thức (Human-in-the-Loop).
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models
"""
from django.db import models
from .group import ChatGroup
from .knowledge import KnowledgeUnit

class ConflictResolutionLog(models.Model):
    """
    Model: ConflictResolutionLog
    Mô tả: Lưu trữ thông tin chi tiết về các điểm xung đột tri thức (Semantic Overlap > 0.85).
    Đảm bảo tính tách biệt với Source of Truth (KnowledgeUnit) để giữ bảng chính luôn sạch, 
    đồng thời hỗ trợ giao diện Tab-based Dashboard cho Quản trị viên.
    """
    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('in_progress', 'Đang sửa đổi (AI Rewrite)'),
        ('resolved', 'Đã hợp nhất / Ghi đè'),
        ('discarded', 'Đã hủy / Giữ cũ'),
    )

    group = models.ForeignKey(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name="conflict_logs",
        verbose_name="Nhóm chat"
    )
    knowledge_unit = models.ForeignKey(
        KnowledgeUnit, 
        on_delete=models.CASCADE, 
        related_name="conflict_logs",
        verbose_name="Đơn vị kiến thức xung đột"
    )
    
    # 📝 Lưu trữ nội dung phục vụ giao diện Side-by-side Diff
    original_content = models.TextField(verbose_name="Nội dung gốc hiện tại")
    conflicting_content = models.TextField(verbose_name="Nội dung mới gây xung đột")
    proposed_content = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Nội dung đề xuất (AI Rewrite / User Edit)"
    )
    
    conflict_reason = models.TextField(verbose_name="Lý do mâu thuẫn từ System Auditor")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name="Trạng thái xử lý"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm phát sinh")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm giải quyết")

    class Meta:
        verbose_name = "Nhật ký xung đột tri thức"
        verbose_name_plural = "Danh sách nhật ký xung đột tri thức"
        indexes = [
            # 🚀 Tối ưu hóa truy vấn Dashboard theo từng nhóm và trạng thái chờ xử lý
            models.Index(fields=['group', 'status'], name='idx_conflict_group_status'),
        ]

    def __str__(self):
        return f"Xung đột [{self.group.name}] - KU #{self.knowledge_unit_id} ({self.get_status_display()})"