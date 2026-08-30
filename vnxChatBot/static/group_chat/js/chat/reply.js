/**
 * File: static/group_chat/js/chat/reply.js
 * Mục đích: Quản lý tính năng trích dẫn và trả lời tin nhắn (Reply System) 
 *           giúp duy trì ngữ cảnh hội thoại mạch lạc trong workspace nhóm vnxChatBot.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 * Module liên kết: ChatWebSocketClient, main.js
 */

class ChatReplyManager {
    constructor() {
        this.currentReplyToId = null;
        this.initReplyEvents();
    }

    initReplyEvents() {
        const chatMessagesContainer = document.getElementById('#message-list-container');
        if (!chatMessagesContainer) return;

        chatMessagesContainer.addEventListener('click', (e) => {
            const replyBtn = e.target.closest('.btn-reply-message');
            if (replyBtn) {
                const messageItem = replyBtn.closest('.message-item');
                const messageId = messageItem?.dataset.messageId;
                if (messageId) {
                    this.prepareReply(messageId);
                }
            }
        });
    }

    prepareReply(messageId) {
        const messageItem = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageItem) return;

        const senderName = messageItem.dataset.senderName || 'Thành viên';
        const messageText = messageItem.querySelector('.message-content-text')?.innerText || '';

        this.setReplyTarget(messageId, senderName, messageText);
    }

    setReplyTarget(messageId, senderName, messageText) {
        this.currentReplyToId = messageId;

        let previewBox = document.getElementById('reply-preview-container');
        if (!previewBox) {
            const chatForm = document.getElementById('chat-form');
            if (chatForm) {
                previewBox = document.createElement('div');
                previewBox.id = 'reply-preview-container';
                previewBox.className = 'p-2 mb-2 bg-light border-start border-primary border-4 rounded small d-flex justify-content-between align-items-center shadow-sm';
                chatForm.prepend(previewBox);
            }
        }

        if (previewBox) {
            previewBox.innerHTML = `
                <div class="text-truncate">
                    <span class="fw-bold text-primary">Đang trả lời ${senderName}:</span>
                    <span class="text-muted ms-1">${messageText.substring(0, 60)}...</span>
                </div>
                <button type="button" class="btn-close btn-sm" onclick="window.chatReplyManager.clearReplyTarget()" aria-label="Close"></button>
            `;
            previewBox.style.display = 'flex';
        }

        const inputField = document.getElementById('chat-message-input');
        if (inputField) inputField.focus();
    }

    clearReplyTarget() {
        this.currentReplyToId = null;
        const previewBox = document.getElementById('reply-preview-container');
        if (previewBox) {
            previewBox.style.display = 'none';
            previewBox.innerHTML = '';
        }
    }

    getReplyTargetId() {
        return this.currentReplyToId;
    }
}

// 🔗 Đưa hàm cầu nối ra không gian tên toàn cục (window) để tránh lỗi ReferenceError
window.prepareReplyMessage = function (messageId) {
    if (window.chatReplyManager && typeof window.chatReplyManager.prepareReply === 'function') {
        window.chatReplyManager.prepareReply(messageId);
    } else {
        console.error("[ChatReplyManager] window.chatReplyManager chưa được khởi tạo!");
    }
};

window.initReplySystem = function () {
    if (typeof window.chatReplyManager === 'undefined') {
        window.chatReplyManager = new ChatReplyManager();
        console.log("[ChatReplyManager] Khởi tạo thành công hệ thống trích dẫn tin nhắn.");
    }
};

// Tự động kích hoạt khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.initReplySystem === 'function') {
        window.initReplySystem();
    }
});