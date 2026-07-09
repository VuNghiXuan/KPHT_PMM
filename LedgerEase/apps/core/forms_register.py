from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Company

class RegistrationForm(forms.Form):
    username = forms.CharField(label="Tên đăng nhập")
    password = forms.CharField(widget=forms.PasswordInput, label="Mật khẩu")
    company_name = forms.CharField(label="Tên công ty của bạn")
    tax_code = forms.CharField(label="Mã số thuế")