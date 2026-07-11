def company_list(request):
    if request.user.is_authenticated:
        # Lấy danh sách công ty người dùng được quyền truy cập
        return {'available_companies': request.user.companies.all()}
    return {'available_companies': []}