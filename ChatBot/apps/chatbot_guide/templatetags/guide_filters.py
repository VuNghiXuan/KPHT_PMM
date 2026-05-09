import re
import unicodedata
import markdown
from django import template
from django.utils.safestring import mark_safe


register = template.Library()

@register.filter(name='markdown')
def markdown_format(text):
    if not text:
        return ""
    # Các extensions này giúp hỗ trợ code block và bảng biểu chuẩn đét
    html = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])
    return mark_safe(html)


@register.filter(name='highlight')
def highlight_search(text, search):
    print(f"--- DEBUG HIGHLIGHT ---")
    print(f"Từ khóa nhận được: '{search}'")
    
    if not search or not text:
        print("Kết quả: Trống hoặc không có từ khóa")
        return mark_safe(text)

    # Chuẩn hóa để so sánh chính xác
    text = unicodedata.normalize('NFC', str(text))
    search = unicodedata.normalize('NFC', str(search))

    pattern = re.compile(re.escape(search), re.IGNORECASE)
    
    # Đếm số lần tìm thấy trước khi replace
    matches = pattern.findall(text)
    print(f"Số lần tìm thấy từ khóa trong nội dung: {len(matches)}")

    def replace_func(match):
        return f'<span style="background-color: #ffeb3b; color: #000;">{match.group(0)}</span>'

    parts = re.split(r'(<[^>]+>)', text)
    for i in range(len(parts)):
        if not parts[i].startswith('<'):
            parts[i] = pattern.sub(replace_func, parts[i])

    result = "".join(parts)
    # Print ra một đoạn kết quả để xem có thẻ <span> chưa
    print(f"Đoạn đầu kết quả sau xử lý: {result[:100]}...") 
    print(f"-----------------------")
    
    return mark_safe(result)