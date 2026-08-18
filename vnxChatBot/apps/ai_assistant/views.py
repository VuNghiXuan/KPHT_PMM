# """
# Mục đích: Cung cấp API/Dashboard cho Admin xem danh sách kiến thức đã duyệt.
# Tác giả: Kiến trúc sư VnxChatBot
# """
# from django.shortcuts import get_object_or_404
# from django.http import JsonResponse
# from apps.group_chat.models import ChatGroup, Membership
# from .services.rag_engine import RAGEngine

# def knowledge_dashboard(request, group_id):
#     """
#     View trả về danh sách kiến thức đã duyệt của nhóm.
#     Chỉ Admin nhóm mới được quyền xem.
#     """
#     # 1. Kiểm tra quyền Admin (Security Check)
#     membership = get_object_or_404(Membership, group_id=group_id, user=request.user)
#     if membership.role != 'admin':
#         return JsonResponse({"error": "Bạn không có quyền truy cập."}, status=403)

#     # 2. Truy vấn dữ liệu qua RAGEngine
#     engine = RAGEngine()
#     active_knowledge = engine.get_all_active_knowledge(group_id)

#     # 3. Trả về JSON
#     return JsonResponse({
#         "group_id": group_id,
#         "knowledge_count": len(active_knowledge),
#         "data": active_knowledge
#     }, safe=False)