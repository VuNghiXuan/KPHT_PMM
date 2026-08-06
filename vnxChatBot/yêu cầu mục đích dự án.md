NỘI DUNG CHỈ DẪN CHO AI (SYSTEM INSTRUCTIONS - NEXUSCHAT)1. Vai trò & Định hướngBạn là kỹ sư phần mềm cao cấp, chuyên gia kiến trúc dự án Django, hỗ trợ dự án NexusChat – Hệ thống nền tảng quản trị năng suất và kết nối làm việc nhóm với AI là thành viên cốt lõi.2. Quy trình Tư duy Kiến trúc (Architecture Thinking Process)Bước 1: Tư duy nghiệp vụ (User Story): Xác định "Ai làm gì, ở đâu, khi nào". (Ví dụ: Hệ thống tự tạo nhóm mặc định khi đăng ký thành công).Bước 2: Vẽ Luồng (Flowchart): Xác định đường đi của dữ liệu từ Người dùng -> FileProcessor -> VectorStore -> LLM.Bước 3: Vẽ ERD: Chỉ vẽ sau khi chốt Flowchart. Dữ liệu phải gắn với group_id.Tư duy ngược: Luôn đặt câu hỏi: "Nếu xóa nhóm hoặc thành viên, dữ liệu liên quan (tin nhắn, vector kiến thức) sẽ được xử lý ra sao để tránh rác hệ thống?".3. Tiêu chuẩn Documentation (Nghiêm ngặt)File-level: Ghi rõ mục đích, tác giả, module liên kết.Class-level (Google Style): Giải thích mục đích, kế thừa, vai trò.Logic phức tạp: Giải thích "Tại sao" (Why) thay vì "Cái gì" (What), đặc biệt là logic RAG và Feedback Loop.Database (Models): Mọi field bắt buộc phải có verbose_name và help_text.4. Kiến trúc Modular Monolith & Nghiệp vụ NexusChatapps.core: Nền tảng (User, Profile, Auth). Khi User đăng ký thành công, hệ thống tự động khởi tạo 1 ChatGroup cơ bản.  apps.group_chat: Quản lý thành viên (dùng is_ai=True cho AI, không tạo User ảo), upload tài liệu (lưu local media/groups/<group_id>/), thảo luận, và Feedback (Like/Dislike).apps.ai_assistant: AI Brain (Vector DB, RAG Engine).apps.subscriptions: Quản lý gói (Gói Free: 5 thành viên + 1 AI).5. Tư duy vận hành & AI Integration (Đặc thù NexusChat)Group-Centric: Mọi dữ liệu phải là group_id tenant.  AI-as-a-Team-Member: AI theo dõi thảo luận âm thầm, học kiến thức mới từ tài liệu upload và tin nhắn người dùng.  Feedback Loop (Thông minh): Khi AI sai, người dùng phản hồi. AI hỏi lại để xác nhận đúng -> Tóm tắt -> Người dùng duyệt -> AI cập nhật kiến thức mới vào phiên bản (Version Control) của Vector DB.  Factory Pattern: Gọi LLM qua AIFactory để linh hoạt giữa các Provider và bảo mật API Key qua .env.  Cost Efficiency: Xử lý cục bộ (EasyOCR, Spacy) trước khi gửi dữ liệu cho LLM.  6. Quy tắc trao đổiKhi tôi gửi code, luôn đính kèm Docstring và giải thích logic.Mọi tệp tin upload lên nhóm phải tự động xử lý qua FileProcessor -> VectorStore (dùng Django Signals).  Luôn ưu tiên sự đơn giản trong code nhưng chặt chẽ trong kiến trúc để dự án dễ dàng mở rộng.  Lưu ý cho AI: Dự án này không sử dụng các khái niệm cũ như CompanyScopedModel hay CompanyMiddleware từ các hệ thống cũ. Mọi logic phân tách dữ liệu phải tập trung vào ChatGroup. 



Phần chưa làm:
Kiểm tra luồng Chat & AI Assistant: Gửi tin nhắn trực tiếp qua giao diện nhóm chat để kiểm tra xem ChatConsumer và mô hình AI phản hồi qua WebSocket có hoạt động trơn tru không.

Cải tiến logic should_trigger_ai trong consumers.py: Tối ưu hóa điều kiện kích hoạt phản hồi của AI (ví dụ: chỉ phản hồi khi được gọi tên @AI hoặc khi có câu hỏi mang tính chất tra cứu tri thức).


🗓️ Tóm tắt kế hoạch công việc cho ngày mai khi bạn quay lại:Ôn lại ngữ cảnh: Tiếp tục từ phần hoàn thiện tính năng chat thời gian thực giữa các thành viên trong nhóm thông qua WebSocket (ChatConsumer) kết hợp với luồng gọi trợ lý AI (@ai) và RAG Engine.  Triển khai code chi tiết:Hoàn thiện mã nguồn Consumer quản lý group_id (Tenant Isolation).  Tích hợp giao diện chat động (chat_detail.html và các partial templates).  Đảm bảo luồng xử lý tài liệu thông qua FileProcessor và kích hoạt tự động qua Django Signals.  


Tao mô tả lại nhé: Hiện tại ở màn hành chat người đang đăng nhập khi vừa mới gởi tin nhắn xong thì nó là nền xanh cho đến khi nhấn f5 thì tin nhắn đó mới hiện đúng fỏm và mẫu tao cần màu vàng (khung này hiện nay thiếu tên hoặc bị mờ người đăng nhập). Tao muốn đồng bộ tin trước khi nhắn và đang nhắn đều có màu vàng form chữ rõ nét và đồng bộ. Mày mô tả lại xem hiểu ý chưa


Mai bắt giải thích chỗ này:
Phân tích nguyên nhân lỗi HTTP 500 (Internal Server Error)
Nhìn vào đoạn mã nguồn hiện tại của hàm knowledge_action_view:

Python
@login_required
@require_POST
def knowledge_action_view(request, knowledge_id, action):
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id)
    
    # Kiểm tra quyền bảo mật tenant qua nhóm chứa document của KnowledgeUnit
    group = ku.document.group if ku.document else getattr(ku, 'group', None)
    if group:
        membership = Membership.objects.filter(group=group, user=request.user).first()
        ...
Và so sánh với URL mà Javascript vừa gọi thực tế:
POST [http://127.0.0.1:8000/groups/15/knowledge/34/action/](http://127.0.0.1:8000/groups/15/knowledge/34/action/)

Nguyên nhân gây ra lỗi 500:

Trong định nghĩa urls.py hiện tại của bạn:

Python
path('<int:group_id>/knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
Đường dẫn này yêu cầu truyền tham số group_id vào hàm view. Tuy nhiên, chữ ký (signature) hiện tại của hàm knowledge_action_view(request, knowledge_id, action) lại thiếu tham số group_id.

Khi Django cố gắng phân giải URL có chứa group_id=15, hàm view không nhận được tham số này dẫn đến ngoại lệ TypeError (Internal Server Error 500).

Giải pháp khắc phục triệt để
Cập nhật lại chữ ký và logic kiểm tra bên trong knowledge_action_view tại tệp chứa view (thường nằm trong apps/group_chat/views/knowledge_views.py hoặc apps/group_chat/views.py) để tiếp nhận group_id và xác thực bảo mật tenant chính xác theo chuẩn Group-Centric:

Python
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST
def knowledge_action_view(request, group_id, knowledge_id, action):
    """
    Function: knowledge_action_view
    Description:
        Thực hiện hành động trong Vòng đời tri thức (Knowledge Lifecycle): 
        Phê duyệt (approve) hoặc rollback (thu hồi) đối với KnowledgeUnit theo group_id.
    """
    # 1. Lấy KnowledgeUnit và đảm bảo thuộc đúng group_id (Tenant Isolation)
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id, document__group_id=group_id)
    
    # 2. Kiểm tra quyền thành viên trong nhóm
    membership = Membership.objects.filter(group_id=group_id, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện tác vụ này trong nhóm!'}, status=403)

    if action == 'approve':
        ku.status = 'approved'
        ku.save()  # Signal sẽ tự động đồng bộ vào Vector DB
        logger.info(f"✅ KnowledgeUnit ID {knowledge_id} trong nhóm {group_id} đã được duyệt (approved).")
        return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
        
    elif action == 'rollback':
        ku.status = 'rollback'
        ku.save()  # Signal sẽ tự động dọn dẹp Vector Store
        logger.info(f"🔄 KnowledgeUnit ID {knowledge_id} trong nhóm {group_id} đã bị thu hồi (rollback).")
        return JsonResponse({'status': 'success', 'message': 'Đã rollback tri thức và xóa khỏi Vector DB!'})
        
    return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ!'}, status=400)