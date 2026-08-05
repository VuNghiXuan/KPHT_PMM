/**
 * File: static/group_chat/js/func_for_group_detail.js
 * Mục đích: Quản lý toàn bộ giao diện và kết nối thời gian thực trong phòng chat nhóm (Group-Centric).
 * Tính năng: 
 *   - Kết nối WebSocket tự động theo group_id.
 *   - Xử lý render tin nhắn, avatar, trích dẫn (Reply).
 *   - Tích hợp FileProcessor upload tài liệu ngầm.
 *   - Quản lý Feedback Loop và đưa tin nhắn vào Kho tri thức nhóm.
 */

class ChatManager {
    constructor() {
        // Lấy các vùng chứa dữ liệu DOM cốt lõi
        this.chatMessagesContainer = document.getElementById('chat-messages');
        if (!this.chatMessagesContainer) return;

        // Đọc cấu hình tenant từ thuộc tính HTML
        this.groupId = this.chatMessagesContainer.dataset.groupId || this.chatMessagesContainer.getAttribute('data-group-id');
        this.currentUsername = window.currentUsername || this.chatMessagesContainer.dataset.currentUsername;
        this.csrfToken = this.chatMessagesContainer.dataset.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        // Trạng thái Reply hiện tại
        this.currentReplyToId = null;

        // Khởi tạo các thành phần
        this.initWebSocket();
        this.initEventListeners();
        this.scrollToBottom();
    }

    /**
     * Khởi tạo kết nối WebSocket bảo mật thời gian thực
     */
    initWebSocket() {
        if (!this.groupId || this.groupId === 'undefined') {
            console.error("❌ Lỗi: Không tìm thấy Group ID hợp lệ cho WebSocket!");
            return;
        }

        const wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";
        const wsUrl = `${wsScheme}${window.location.host}/ws/groups/${this.groupId}/`;

        if (typeof window.chatSocket === 'undefined' || !window.chatSocket) {
            window.chatSocket = new WebSocket(wsUrl);
        }

        this.socket = window.chatSocket;

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.appendMessage(data);
        };

        this.socket.onclose = () => {
            console.warn("⚠️ WebSocket chat socket đã ngắt kết nối.");
        };

        this.socket.onerror = (error) => {
            console.error("❌ Lỗi WebSocket:", error);
        };
    }

    /**
     * Đăng ký các sự kiện tương tác trên giao diện (Form gửi tin, Upload file...)
     */
    initEventListeners() {
        // 1. Xử lý gửi tin nhắn qua Form
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-message-input') || document.getElementById('chat-input');
        const chatSubmitBtn = document.getElementById('chat-message-submit');

        if (chatForm && chatInput) {
            chatForm.onsubmit = (e) => {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (!message) return;

                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({
                        'message': message,
                        'reply_to_id': this.currentReplyToId
                    }));
                    chatInput.value = '';
                    this.cancelReply();
                } else {
                    alert("❌ Kết nối WebSocket chưa sẵn sàng.");
                }
            };
        }

        if (chatSubmitBtn && chatInput && chatForm) {
            chatSubmitBtn.onclick = (e) => {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            };
        }

        // 2. Xử lý Upload file qua FileProcessor
        const fileUploadInput = document.getElementById('file-upload');
        if (fileUploadInput) {
            fileUploadInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const loadingDiv = document.createElement('div');
                loadingDiv.id = 'upload-loading';
                loadingDiv.className = 'd-flex justify-content-start mb-3 px-2';
                loadingDiv.innerHTML = `
                    <div class="p-3 rounded-4 shadow-sm bg-white border text-primary">
                        <i class="fas fa-spinner fa-spin me-2"></i> Hệ thống đang xử lý và trích xuất tri thức từ file <b>${file.name}</b> qua FileProcessor... 🧠
                    </div>
                `;
                this.chatMessagesContainer.appendChild(loadingDiv);
                this.scrollToBottom();

                const formData = new FormData();
                formData.append('file', file);
                const uploadUrl = fileUploadInput.dataset.uploadUrl;

                fetch(uploadUrl, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-CSRFToken': this.csrfToken }
                })
                    .then(response => {
                        document.getElementById('upload-loading')?.remove();
                        return response.json();
                    })
                    .then(data => {
                        if (data.status === 'success') {
                            alert("✅ " + data.message);
                            location.reload();
                        } else {
                            alert('⚠️ Lỗi tải lên: ' + (data.message || 'Không thể xử lý tệp tin.'));
                        }
                    })
                    .catch(error => {
                        document.getElementById('upload-loading')?.remove();
                        console.error('Upload Error:', error);
                        alert('❌ Đã xảy ra lỗi kết nối khi xử lý FileProcessor.');
                    });
            });
        }
    }

    /**
     * Render tin nhắn mới nhận từ WebSocket vào khung chat
     */
    appendMessage(data) {
        const isMe = data.sender_name === this.currentUsername;
        const messageDiv = document.createElement('div');

        messageDiv.className = `d-flex ${data.is_ai || !isMe ? 'justify-content-start' : 'justify-content-end'} mb-3 message-item position-relative`;
        messageDiv.setAttribute('data-message-id', data.message_id);

        let cardClass = data.is_ai ? 'vnx-ai-message-card' : (isMe ? 'vnx-user-message-card' : 'vnx-other-message-card');
        let headerBoxClass = data.is_ai ? 'vnx-ai-header-box' : (isMe ? 'vnx-user-header-box' : 'vnx-other-header-box');
        let toolbarPosition = isMe && !data.is_ai ? 'toolbar-left' : 'toolbar-right';
        const timeString = data.created_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Xử lý trích dẫn Reply nếu có
        let replyQuoteHTML = '';
        if (data.reply_to) {
            replyQuoteHTML = `
                <div class="bg-light border-start border-secondary border-3 p-2 mb-2 rounded-end small text-muted">
                    <strong>${data.reply_to.sender_name}:</strong>
                    <p class="mb-0 text-truncate">${data.reply_to.content}</p>
                </div>
            `;
        }

        // Xử lý hiển thị Avatar người gửi hoặc AI
        let avatarHTML = '';
        if (data.is_ai) {
            avatarHTML = `<div class="rounded-circle bg-info text-white d-flex align-items-center justify-content-center shadow-sm" style="width: 38px; height: 38px; font-size: 1.2rem;">🤖</div>`;
        } else if (data.avatar_url) {
            avatarHTML = `<img src="${data.avatar_url}" alt="${data.sender_name}" class="rounded-circle object-fit-cover shadow-sm" width="38" height="38">`;
        } else {
            avatarHTML = `<div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 38px; height: 38px;">${data.sender_name.charAt(0).toUpperCase()}</div>`;
        }

        let myAvatarHTML = '';
        if (!data.is_ai && isMe) {
            if (window.currentUserAvatarUrl) {
                myAvatarHTML = `<div class="flex-shrink-0 ms-2"><img src="${window.currentUserAvatarUrl}" alt="${data.sender_name}" class="rounded-circle object-fit-cover shadow-sm" width="38" height="38"></div>`;
            } else {
                myAvatarHTML = `<div class="flex-shrink-0 ms-2"><div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 38px; height: 38px;">${data.sender_name.charAt(0).toUpperCase()}</div></div>`;
            }
        }

        // Nội dung HTML hoàn chỉnh cho một message bubble
        messageDiv.innerHTML = `
            ${data.is_ai || !isMe ? `<div class="flex-shrink-0 me-2">${avatarHTML}</div>` : ''}
            <div class="message-bubble-wrapper position-relative" style="max-width: 70%;">
                
                <!-- Thanh công cụ nổi thông minh (Hover Action Menu) -->
                <div class="message-hover-toolbar position-absolute shadow bg-white border rounded-pill px-3 py-1 d-flex gap-2 align-items-center ${toolbarPosition}"
                    style="top: -22px; display: none; z-index: 10; font-size: 0.85rem;">
                    <span class="cursor-pointer text-secondary hover-scale"
                        onclick="chatManager.prepareReplyMessage('${data.message_id}', '${data.is_ai ? 'AI Assistant' : data.sender_name}', '${encodeURIComponent(data.content)}')"
                        title="Trả lời tin nhắn này">
                        <i class="fas fa-reply"></i>
                    </span>
                    <span class="border-start mx-1"></span>
                    <span class="cursor-pointer text-primary hover-scale fw-bold d-flex align-items-center gap-1"
                        onclick="chatManager.promoteMessageToKnowledge('${data.message_id}')" title="Đưa tin nhắn này vào kho tri thức nhóm">
                        <i class="fas fa-graduation-cap"></i> Học 🧠
                    </span>
                    <span class="border-start mx-1"></span>
                    <span class="cursor-pointer text-success hover-scale" onclick="chatManager.handleFeedback('${data.message_id}', 'like')" title="Thích">
                        <i class="far fa-thumbs-up"></i>
                    </span>
                    <span class="cursor-pointer text-danger hover-scale" onclick="chatManager.handleFeedback('${data.message_id}', 'heart')" title="Thả tim">
                        <i class="far fa-heart"></i>
                    </span>
                    <span class="cursor-pointer text-muted hover-scale" onclick="chatManager.handleFeedback('${data.message_id}', 'dislike')" title="Không thích">
                        <i class="far fa-thumbs-down"></i>
                    </span>
                </div>

                <div class="card shadow-sm position-relative ${cardClass}">
                    <div class="card-header py-1 px-3 small d-flex justify-content-between align-items-center ${headerBoxClass}">
                        <span class="me-3"><strong>${data.is_ai ? '🤖 AI Assistant' : data.sender_name}</strong></span>
                        <span class="text-secondary opacity-75" style="font-size: 0.75rem;">${timeString}</span>
                    </div>
                    <div class="card-body py-2 px-3">
                        ${replyQuoteHTML}
                        <p class="mb-0 text-break">${data.content}</p>
                    </div>
                </div>
            </div>
            ${!data.is_ai && isMe ? myAvatarHTML : ''}
        `;

        this.chatMessagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /**
     * Chuẩn bị trạng thái trả lời (Reply)
     */
    prepareReplyMessage(messageId, senderName, encodedContent) {
        this.currentReplyToId = messageId;
        const content = decodeURIComponent(encodedContent);

        const previewBar = document.getElementById('reply-preview-bar');
        const usernameSpan = document.getElementById('reply-to-username');
        const contentP = document.getElementById('reply-to-content');

        if (previewBar && usernameSpan && contentP) {
            usernameSpan.textContent = senderName;
            contentP.textContent = content;
            previewBar.classList.remove('d-none');
            previewBar.classList.add('d-flex');
        }

        const chatInput = document.getElementById('chat-message-input') || document.getElementById('chat-input');
        if (chatInput) chatInput.focus();
    }

    /**
     * Hủy bỏ trạng thái Reply
     */
    cancelReply() {
        this.currentReplyToId = null;
        const previewBar = document.getElementById('reply-preview-bar');
        if (previewBar) {
            previewBar.classList.remove('d-flex');
            previewBar.classList.add('d-none');
        }
    }

    /**
     * Chuyển đổi tin nhắn thành Tri thức nhóm (KnowledgeUnit)
     */
    promoteMessageToKnowledge(messageId) {
        fetch(`/groups/message/${messageId}/promote-knowledge/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            }
        })
            .then(res => res.json())
            .then(data => {
                alert(data.message || "Đã gửi yêu cầu cập nhật tri thức vào kho học tập nhóm!");
            })
            .catch(err => console.error('Promote Knowledge Error:', err));
    }

    /**
     * Xử lý thả cảm xúc phản hồi (Feedback Loop)
     */
    handleFeedback(messageId, feedbackType) {
        fetch(`/groups/message/${messageId}/feedback/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({ type: feedbackType })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
                    if (messageEl && data.total_count !== undefined) {
                        if (data.total_count === 0) {
                            messageEl.querySelector('.reactions-badge-container')?.remove();
                        } else {
                            location.reload(); // Làm mới nhẹ để hiển thị số lượng badge cập nhật
                        }
                    }
                } else {
                    console.warn("⚠️ Phản hồi từ server:", data.message);
                }
            })
            .catch(error => console.error('❌ Lỗi kết nối Feedback:', error));
    }

    /**
     * Cuộn khung nhìn xuống tin nhắn mới nhất
     */
    scrollToBottom() {
        if (this.chatMessagesContainer) {
            this.chatMessagesContainer.scrollTop = this.chatMessagesContainer.scrollHeight;
        }
    }
}

// Khởi tạo ChatManager khi trang tải xong
document.addEventListener("DOMContentLoaded", function () {
    window.chatManager = new ChatManager();
});