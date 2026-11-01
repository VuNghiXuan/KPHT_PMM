# config/context_processors.py
def user_features(request):
    """
    Không hiển thị những gì được cấp quyền cho khách, context_processor để các menu trên thanh điều hướng (navigation) tự ẩn hiện"""
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        company = request.user.profile.company
        if company.plan:
            # Trả về danh sách slug các tính năng công ty được quyền dùng
            return {'allowed_features': list(company.plan.features.values_list('slug', flat=True))}
    return {'allowed_features': []}