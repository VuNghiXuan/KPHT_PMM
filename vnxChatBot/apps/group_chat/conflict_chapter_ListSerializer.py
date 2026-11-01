# -*- coding: utf-8 -*-
"""
Module: apps.group_chat.serializers
Mục đích: Serializer chuyển đổi danh sách KnowledgeChapter bị xung đột sang cấu trúc JSON.
"""

from rest_framework import serializers
from apps.group_chat.models import KnowledgeChapter

class ConflictChapterListSerializer(serializers.ModelSerializer):
    reason = serializers.SerializerMethodField()
    conflict_with = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeChapter
        fields = [
            'id', 
            'title', 
            'summary', 
            'chapter_index', 
            'status', 
            'suggested_content', 
            'reason', 
            'conflict_with',
            'updated_at'
        ]

    def get_reason(self, obj):
        if isinstance(obj.metadata, dict):
            return obj.metadata.get("reason", "Phát hiện trùng lặp ngữ nghĩa cao trong nhóm.")
        return "Phát hiện trùng lặp ngữ nghĩa cao trong nhóm."

    def get_conflict_with(self, obj):
        if isinstance(obj.metadata, dict):
            return obj.metadata.get("conflict_with", [])
        return []