# apps/chatbot_guide/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Prefetch
from django.urls import reverse
from .models import GuideCategory, GuideEntry

def guide_view(request, entry_id=None):
    query = request.GET.get('q', '').strip()
    
    # 1. Chỉ lấy những bài đã được ANH VŨ DUYỆT (is_reviewed=True)
    reviewed_entries = GuideEntry.objects.filter(is_reviewed=True)
    
    # 2. Xử lý Sidebar mặc định (Pre-load để tăng tốc)
    categories = GuideCategory.objects.all().prefetch_related(
        Prefetch('entries', queryset=reviewed_entries)
    )
    
    current_entry = None
    search_results = reviewed_entries.none()  # Khởi tạo giá trị rỗng mặc định để tránh lỗi UnboundLocal

    # 3. Ưu tiên 1: Click trực tiếp từ Sidebar
    if entry_id:
        current_entry = get_object_or_404(reviewed_entries, id=entry_id)
    
    # 4. Xử lý Tìm kiếm (Search)
    if query:
        # Đồng bộ tìm kiếm đa trường: Tiêu đề, Nội dung, Kiến thức cần có, Ghi chú tương lai
        search_results = reviewed_entries.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(prerequisites__icontains=query) |
            Q(future_notes__icontains=query)
        ).distinct()
        
        # Nếu chỉ trúng 1 bài duy nhất -> Nhảy thẳng vào bài đó
        if search_results.count() == 1 and not entry_id:
            first_id = search_results.first().id
            target_url = reverse('chatbot_guide:detail', kwargs={'entry_id': first_id})
            return redirect(f"{target_url}?q={query}")
        
        # Lọc Sidebar: Chỉ hiện các Danh mục có bài khớp với từ khóa
        categories = GuideCategory.objects.filter(
            Q(name__icontains=query) | Q(entries__in=search_results)
        ).distinct().prefetch_related(
            Prefetch('entries', queryset=search_results)
        )

        # Ưu tiên 2: Nếu đang search mà chưa chọn bài, lấy bài đầu tiên của kết quả search
        if not current_entry and search_results.exists():
            current_entry = search_results.first()
    
    # 5. Ưu tiên 3: Trang chủ (Mới vào, không search, không chọn bài)
    if not current_entry:
        # Lấy bài đầu tiên của danh mục có thứ tự nhỏ nhất
        first_cat = categories.filter(entries__isnull=False).first()
        if first_cat:
            current_entry = first_cat.entries.all().first()

    context = {
        'categories': categories,
        'current_entry': current_entry,
        'query': query,
        # Trả thêm số lượng kết quả để hiển thị thông báo "Tìm thấy X bài học"
        'result_count': search_results.count() if query else 0 
    }
    
    return render(request, 'chatbot_guide/guide.html', context)