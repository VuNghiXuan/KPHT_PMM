/**
 * File: static/group_chat/js/chat/reactions.js
 * Mục đích: Quản lý tính năng tương tác tin nhắn, thả cảm xúc (Feedback Loop) 
 *           và thúc đẩy đưa tin nhắn thành tri thức nhóm (KnowledgeUnit) trong workspace vnxChatBot.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 * Module liên kết: main.js
 */

class ChatReactions {
    constructor() {
        this.initReactionEvents();
    }

    initReactionEvents() {
        const chatMessagesContainer = document.getElementById('chat-messages');
        if (!chatMessagesContainer) {
            console.warn("[ChatReactions] Không tìm thấy vùng chứa #chat-messages để gắn sự kiện tương tác.");
            return;
        }

        chatMessagesContainer.addEventListener('mouseover', (e) => {
            const messageItem = e.target.closest('.message-item');
            if (messageItem) {
                const toolbar = messageItem.querySelector('.message-hover-toolbar');
                if (toolbar) toolbar.style.display = 'flex';
            }
        });

        chatMessagesContainer.addEventListener('mouseout', (e) => {
            const messageItem = e.target.closest('.message-item');
            if (messageItem) {
                if (!messageItem.contains(e.relatedTarget)) {
                    const toolbar = messageItem.querySelector('.message-hover-toolbar');
                    if (toolbar) toolbar.style.display = 'none';
                }
            }
        });
    }

    /**
     * Gửi yêu cầu thả cảm xúc phản hồi (Feedback Loop) lên hệ thống.
     */
    static handleFeedback(messageId, feedbackType) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch(`/groups/message/${messageId}/feedback/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ type: feedbackType })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log(`[ChatReactions] ✅ Đã ghi nhận phản hồi [${feedbackType}] cho tin nhắn ${messageId}`);
                    location.reload();
                } else {
                    console.warn("⚠️ Phản hồi từ server:", data.message);
                }
            })
            .catch(error => console.error('❌ Lỗi kết nối Feedback Loop:', error));
    }

    /**
     * Chuyển đổi tin nhắn thành Tri thức nhóm (KnowledgeUnit).
     * Cập nhật trực tiếp số lượng badge chờ duyệt trên UI mà không cần tải lại trang.
     */
    static promoteToKnowledge(messageId) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch(`/groups/message/${messageId}/promote-knowledge/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message || "🧠 Đã đưa tin nhắn vào hàng đợi phê duyệt (Pending) thành công!");
                    console.log(`[KnowledgeLifecycle] 🧠 Tin nhắn ${messageId} đã được đưa vào hàng đợi phê duyệt.`);

                    // 🚀 Cập nhật giao diện tự động: Tăng số lượng badge "Chờ duyệt" thêm 1
                    const unapprovedBadge = document.getElementById('unapproved-count');
                    if (unapprovedBadge) {
                        let currentCount = parseInt(unapprovedBadge.innerText) || 0;
                        unapprovedBadge.innerText = currentCount + 1;
                    }
                } else {
                    alert("⚠️ " + (data.message || "Không thể thực hiện hành động này."));
                }
            })
            .catch(err => {
                console.error('❌ Lỗi Promote Knowledge:', err);
                alert('❌ Lỗi kết nối hoặc xử lý hệ thống.');
            });
    }
}

// 🔗 ĐĂNG KÝ HÀM RA TOÀN CỤC (WINDOW SCOPE) ĐỂ TRÁNH LỖI REFERENCE ERROR
window.handleFeedback = ChatReactions.handleFeedback;
window.promoteMessageToKnowledge = ChatReactions.promoteToKnowledge;

/**
 * Hàm khởi tạo toàn cục được gọi từ main.js để kích hoạt module Reactions.
 */
function initChatActions() {
    if (typeof window.chatReactions === 'undefined') {
        window.chatReactions = new ChatReactions();
        console.log("[ChatReactions] Khởi tạo thành công module quản lý tương tác tin nhắn.");
    }
}