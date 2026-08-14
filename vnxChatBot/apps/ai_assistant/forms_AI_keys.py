"""
File: apps/ai_assistant/forms.py
Mục đích: Form cấu hình AI cho người dùng.
"""
from django import forms
from .models import GroupAIProvider

class AIProviderForm(forms.ModelForm):
    class Meta:
        model = GroupAIProvider
        fields = ['provider', 'api_key', 'model_name', 'is_default']
        widgets = {
            'api_key': forms.PasswordInput(render_value=True),
        }