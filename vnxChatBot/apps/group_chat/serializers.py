# -*- coding: utf-8 -*-
from rest_framework import serializers

class AIActionSerializer(serializers.Serializer):
    """
    Serializer để validate dữ liệu từ request handleAIRewrite.
    Chỉ kiểm tra user_prompt và action_type, chapter_id được lấy từ URL.
    """
    user_prompt = serializers.CharField(required=True, min_length=5, max_length=1000)
    action_type = serializers.CharField(default='rewrite')

    def validate_action_type(self, value):
        allowed_actions = ['rewrite', 'summarize', 'expand', 'fix_tone']
        if value not in allowed_actions:
            raise serializers.ValidationError(f"Action '{value}' không được hỗ trợ.")
        return value