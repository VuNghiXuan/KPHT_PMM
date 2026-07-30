from apps.group_chat.models import Membership
def company_list(request):
    if request.user.is_authenticated:
        # Lấy danh sách công ty người dùng được quyền truy cập
        return {'available_companies': request.user.companies.all()}
    return {'available_companies': []}


def user_groups_processor(request):
    """
    Context Processor cung cấp danh sách nhóm của user hiện tại cho mọi template (dùng ở base.html).
    """
    if request.user.is_authenticated:
        # Lấy danh sách nhóm thông qua Membership theo chuẩn Group-Centric
        memberships = Membership.objects.filter(user=request.user).select_related('group')
        groups = [m.group for m in memberships]
        return {'user_groups': groups}
    return {'user_groups': []}