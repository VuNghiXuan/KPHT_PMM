# -*- coding: utf-8 -*-
from django.db import models

class KnowledgeStatus(models.TextChoices):
    PENDING = 'pending', 'Đang chờ xử lý'
    STAGING = 'staging', 'Đang phân tích / Staging'
    READY_TO_APPROVE = 'ready_to_approve', 'Sẵn sàng phê duyệt'
    CONFLICT_DETECTED = 'conflict_detected', 'Phát hiện xung đột'
    APPROVED = 'approved', 'Đã phê duyệt'