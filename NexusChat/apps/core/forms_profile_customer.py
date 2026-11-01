"""
Định nghĩa các Form cho việc thiết lập thông tin người dùng và công ty.
"""
from django import forms
from .models import Profile, Company

class ProfileSetupForm(forms.Form):
    """
    Form dùng để người dùng thiết lập công ty hoặc tham gia công ty trong lần đầu đăng nhập.
    """
    company_name = forms.CharField(
        label="Tên công ty",
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Nhập tên công ty của bạn'})
    )
    tax_code = forms.CharField(
        label="Mã số thuế",
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Ví dụ: 0101234567'})
    )

    def clean_tax_code(self):
        """Kiểm tra mã số thuế có hợp lệ hay đã tồn tại chưa."""
        tax_code = self.cleaned_data.get('tax_code')
        if Company.objects.filter(tax_code=tax_code).exists():
            # Nếu đã tồn tại, sau này bạn có thể logic để cho người dùng Join vào công ty đó
            pass 
        return tax_code

    def save(self, user):
        """
        Logic lưu dữ liệu: Tạo Company mới (nếu chưa có) và gắn vào Profile của User.
        """
        company, created = Company.objects.get_or_create(
            tax_code=self.cleaned_data['tax_code'],
            defaults={'name': self.cleaned_data['company_name']}
        )
        
        # Tạo Profile gắn với User và Company
        profile = Profile.objects.create(
            user=user,
            company=company
        )
        return profile