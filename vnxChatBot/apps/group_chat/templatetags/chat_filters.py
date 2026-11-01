"""
File: apps/group_chat/templatetags/chat_filters.py
Mục đích: Cung cấp các Custom Template Filter hỗ trợ render giao diện chat, 
          đặc biệt là tự động định dạng thẻ mention (@username) chuẩn phong cách vnxChatBot.
Tác giả: Kỹ sư hệ thống vnxChatBot
"""

import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='format_mentions')
def format_mentions(value):
    """
    Quét nội dung văn bản, tự động tìm kiếm các thẻ @username và bọc chúng
    bằng thẻ HTML badge chữ xanh, đồng bộ hoàn toàn với hàm formatMessageMentions bên JS.
    """
    if not value:
        return ""
    
    # Escape dữ liệu thô để bảo mật XSS
    safe_text = escape(str(value))
    
    # Biểu thức chính quy hỗ trợ cả tiếng Việt (Unicode range) khớp với logic Javascript
    mention_regex = r'@([a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]+)'
    
    # Thay thế bằng cấu trúc HTML badge màu xanh giống hệt WebSocket
    formatted_html = re.sub(
        mention_regex,
        r'<span class="badge bg-primary-subtle text-primary fw-bold px-1 rounded">@\1</span>',
        safe_text
    )
    
    return mark_safe(formatted_html)