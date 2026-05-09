from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Prefetch
from django.urls import reverse
from .models import GuideCategory, GuideEntry

def guide_view(request, entry_id=None):
    query = request.GET.get('q', '').strip()
    
    # 1. Lấy toàn bộ danh mục làm gốc
    categories = GuideCategory.objects.all().prefetch_related('entries')
    current_entry = None

    # 2. Ưu tiên 1: Nếu có ID cụ thể từ URL (người dùng click vào sidebar)
    if entry_id:
        current_entry = get_object_or_404(GuideEntry, id=entry_id)
    
    # 3. Xử lý Search
    if query:
        entries = GuideEntry.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()
        
        # Nếu chỉ trúng 1 bài duy nhất và đang ở trang chủ -> Nhảy thẳng vào bài đó kèm query
        if entries.count() == 1 and not entry_id:
            first_id = entries.first().id
            target_url = reverse('chatbot_guide:detail', kwargs={'entry_id': first_id})
            return redirect(f"{target_url}?q={query}")
        
        # Lọc Sidebar theo từ khóa
        categories = GuideCategory.objects.filter(
            Q(name__icontains=query) | Q(entries__in=entries)
        ).distinct().prefetch_related(Prefetch('entries', queryset=entries))

        # Ưu tiên 2: Nếu đang search mà chưa có bài cụ thể, lấy bài đầu tiên của kết quả search
        if not current_entry and entries.exists():
            current_entry = entries.first()
    
    # 4. Ưu tiên 3: Nếu vẫn chưa có bài nào (Vừa vào trang chủ, không search, không ID)
    # Lấy bài đầu tiên của Danh mục đầu tiên trong hệ thống
    if not current_entry:
        # Lấy lại toàn bộ categories để đảm bảo không bị ảnh hưởng bởi bộ lọc search phía trên
        all_categories = GuideCategory.objects.all().prefetch_related('entries')
        first_cat = all_categories.first()
        if first_cat:
            current_entry = first_cat.entries.first()

    context = {
        'categories': categories,
        'current_entry': current_entry,
        'query': query
    }
    
    return render(request, 'chatbot_guide/guide.html', context)