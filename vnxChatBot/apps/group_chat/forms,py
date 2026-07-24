# apps/group_chat/forms.py
from django import forms
from .models import Membership
from apps.core.models import User

class AddMemberForm(forms.Form):
    """
    Form dùng để thêm thành viên mới vào ChatGroup dựa trên username hoặc email.
    """
    username = forms.CharField(
        max_v_length=150, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập username thành viên...'}),
        label="Tên đăng nhập"
    )
    role = forms.ChoiceField(
        choices=Membership.Role.choices, 
        initial=Membership.Role.MEMBER,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Vai trò"
    )