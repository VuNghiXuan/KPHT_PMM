# apps/core/tests.py
import pytest
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_user_has_profile_property():
    User = get_user_model()
    user = User.objects.create_user(username="testuser")
    # Kiểm tra kịch bản chưa có profile
    assert user.has_profile is False