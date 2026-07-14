# apps/group_chat/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.ai_assistant.models import Document
from .models import ChatGroup, Message

# ĐÚNG: Import từ module services mới
from apps.ai_assistant.services.llm_provider import LLMService

@login_required
def group_chat_detail(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)
    messages = Message.objects.filter(group=group).order_by('created_at')[:50]
    
    # Ví dụ cách dùng nếu bạn muốn gọi AI trong View (tuy nhiên khuyên dùng Celery ở tasks.py)
    # llm_service = LLMService()
    
    return render(request, 'group_chat/chat.html', {
        'group': group,
        'messages': messages
    })

@login_required
def upload_document(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)
    if request.method == 'POST':
        file = request.FILES.get('document')
        if file:
            # Document được tạo -> Signal trong ai_assistant sẽ kích hoạt
            Document.objects.create(group=group, file=file)
            return redirect('group_chat:detail', group_id=group_id)
    return redirect('group_chat:detail', group_id=group_id)