"""
File: apps/ai_assistant/forms.py
Mục đích: Form cấu hình AI cho người dùng.
"""
from django import forms
from .models import AIConfig

class AIConfigForm(forms.ModelForm):
    class Meta:
        model = AIConfig
        fields = ['provider', 'api_key', 'model_name', 'is_default']
        widgets = {
            'api_key': forms.PasswordInput(render_value=True),
        }