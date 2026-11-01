# apps/core/forms_register.py
from django import forms
from django.contrib.auth.models import User
from .models import Company

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Mật khẩu")
    company_name = forms.CharField(label="Tên công ty")
    tax_code = forms.CharField(label="Mã số thuế")

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_tax_code(self):
        tax_code = self.cleaned_data.get('tax_code')
        if Company.objects.filter(tax_code=tax_code).exists():
            raise forms.ValidationError("Mã số thuế này đã được đăng ký.")
        return tax_code