/**
 * File: static/group_chat/js/chat/websocket.js
 * Mục đích: Quản lý kết nối WebSocket thời gian thực theo định danh nhóm (Group-Centric),
 *           tự động render tin nhắn, xử lý trích dẫn (Reply Zalo-style) và truyền tải thông điệp.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 * Module liên kết: main.js, reply.js, reactions.js
 */

class ChatWebSocketClient {
    /**
     * Khởi tạo kết nối WebSocket dựa trên Group ID của phòng chat.
     * @param {string|number} [groupId] - Định danh nhóm chat hiện tại (Group-Centric isolation).
     */
    constructor(groupId) {
        const messageContainer = document.getElementById('message-list-container');
        this.groupId = groupId || window.VNXWorkspaceContext?.group?.id || messageContainer?.dataset.groupId;

        this.socket = null;
        this.reconnectInterval = 3000;

        // 🚀 Đăng ký MutationObserver để theo dõi sự thay đổi DOM của khung chat
        if (messageContainer) {
            this.observer = new MutationObserver(() => {
                this.scrollToBottom();
            });
            this.observer.observe(messageContainer, { childList: true });
        }

        this.initConnection();
        this.initChatFormEvents();
    }

    /**
     * Thiết lập kết nối WebSocket bảo mật tới backend Django Channels.
     */
    initConnection() {
        if (!this.groupId || this.groupId === 'undefined') {
            console.error("❌ [WebSocket] Không thể khởi tạo kết nối do thiếu Group ID hợp lệ.");
            return;
        }

        const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        const wsUrl = `${wsProtocol}${window.location.host}/ws/groups/${this.groupId}/`;

        console.log(`🔌 [WebSocket] Đang kết nối tới kênh thời gian thực: ${wsUrl}`);
        this.socket = new WebSocket(wsUrl);

        // 🔗 Đồng bộ alias toàn cục để các module khác có thể tham chiếu an toàn nếu cần
        window.chatSocket = this.socket;

        this.socket.onopen = () => {
            console.log(`✅ [WebSocket] Đã thiết lập kết nối thành công cho nhóm ID: ${this.groupId}`);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("📥 [WebSocket] Nhận được gói tin dữ liệu mới:", data);

                // Tự động render tin nhắn trực tiếp lên giao diện DOM
                this.appendMessage(data);
            } catch (error) {
                console.error("❌ [WebSocket] Lỗi phân tích cú pháp JSON từ dữ liệu nhận:", error);
            }
        };

        this.socket.onclose = (event) => {
            console.warn(`⚠️ [WebSocket] Kết nối đã bị đóng (Code: ${event.code}). Đang thử kết nối lại sau...`);
            setTimeout(() => {
                this.initConnection();
            }, this.reconnectInterval);
        };

        this.socket.onerror = (error) => {
            console.error("❌ [WebSocket] Đã xảy ra lỗi đường truyền WebSocket:", error);
        };
    }

    /**
     * Gửi gói tin dữ liệu đi thông qua kênh WebSocket.
     * @param {Object} payload - Dữ liệu dạng JSON cần gửi lên server.
     */
    send(payload) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(payload));
        } else {
            console.error("❌ [WebSocket] Không thể gửi tin nhắn vì kênh truyền chưa sẵn sàng.");
        }
    }

    /**
     * Lắng nghe sự kiện submit form chat hoặc nhấn Enter để truyền thông điệp đi,
     * tích hợp hoàn toàn hệ thống lấy ID tin nhắn trích dẫn (Reply System).
     */
    initChatFormEvents() {
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('chat-message-input');

        if (!messageInput) {
            console.warn("⚠️ [WebSocket] Không tìm thấy ô nhập liệu #chat-message-input trên giao diện.");
            return;
        }

        const handleSendMessage = () => {
            const messageText = messageInput.value.trim();
            if (!messageText) return;

            // 📥 Lấy ID tin nhắn đang được trích dẫn thông qua ChatReplyManager chuẩn xác
            const replyToId = window.chatReplyManager ? window.chatReplyManager.getReplyTargetId() : null;

            // 🚀 Đóng gói payload đầy đủ thông tin gửi lên Django Consumer
            const payload = {
                message: messageText,
                group_id: this.groupId,
                reply_to_id: replyToId
            };

            console.log("📤 [WebSocket] Đang truyền tin nhắn đi (kèm Reply Context):", payload);
            this.send(payload);

            // Reset ô input và xóa sạch trạng thái preview reply ngay sau khi gửi thành công
            messageInput.value = '';
            if (window.chatReplyManager) {
                window.chatReplyManager.clearReplyTarget();
            }
        };

        if (chatForm) {
            // Ngăn chặn việc đăng ký listener nhiều lần bằng cách gán cờ hoặc kiểm tra
            chatForm.onsubmit = (e) => {
                e.preventDefault();
                handleSendMessage();
            };
        }

        messageInput.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        };
    }

    /**
      * Render tin nhắn mới nhận từ WebSocket vào khung chat với đầy đủ giao diện bong bóng, avatar và toolbar tương tác.
      * @param {Object} data - Dữ liệu tin nhắn nhận từ server qua WebSocket.
      */
    appendMessage(data) {
        // Thành đoạn mới:
        const messagesContainer = document.getElementById('message-list-container');
        if (!messagesContainer) {
            console.warn("⚠️ [WebSocket] Không tìm thấy #message-list-container để hiển thị tin nhắn.");
            return;
        }

        const currentUsername = window.currentUsername || messagesContainer.dataset.username || '';
        const senderName = data.sender_name || data.username || (data.is_ai ? '🤖 AI Assistant' : 'Thành viên');
        // const isMe = senderName === currentUsername;
        const currentUserId = parseInt(messagesContainer.dataset.userId || window.currentUserId);
        const senderId = data.sender_id ? parseInt(data.sender_id) : null;
        const isMe = (senderId !== null && senderId === currentUserId);


        const messageDiv = document.createElement('div');
        const messageId = data.message_id || data.id || '';

        messageDiv.className = `d-flex ${data.is_ai || !isMe ? 'justify-content-start' : 'justify-content-end'} mb-3 message-item position-relative`;
        if (messageId) {
            messageDiv.setAttribute('data-message-id', messageId);
        }
        messageDiv.setAttribute('data-sender-name', senderName);

        let cardClass = data.is_ai ? 'vnx-ai-message-card' : (isMe ? 'vnx-user-message-card' : 'vnx-other-message-card');
        let headerBoxClass = data.is_ai ? 'vnx-ai-header-box' : (isMe ? 'vnx-user-header-box' : 'vnx-other-header-box');
        let toolbarPosition = isMe && !data.is_ai ? 'toolbar-left' : 'toolbar-right';
        const timeString = data.created_at || data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const messageContent = data.content || data.message || '';

        // 💡 Xử lý Escape HTML chống XSS, sau đó truyền qua bộ lọc format mention chữ xanh
        const safeEscapedContent = this.escapeHtml(messageContent);
        const formattedContent = formatMessageMentions(safeEscapedContent);

        // 📥 Xử lý render hộp trích dẫn tin nhắn gốc (Reply Quote Box) khi nhận WebSocket
        let replyQuoteHTML = '';
        if (data.reply_to) {
            const replySender = data.reply_to.sender_name || 'Thành viên';
            const replyText = data.reply_to.content || data.reply_to.message || '';
            replyQuoteHTML = `
                <div class="bg-light border-start border-primary border-3 p-2 mb-2 rounded small text-muted">
                    <span class="fw-bold text-dark">${this.escapeHtml(replySender)}:</span>
                    <p class="mb-0 text-truncate">${this.escapeHtml(replyText)}</p>
                </div>
            `;
        }

        let avatarHTML = '';
        if (data.is_ai) {
            avatarHTML = `<div class="rounded-circle bg-info text-white d-flex align-items-center justify-content-center shadow-sm" style="width: 38px; height: 38px; font-size: 1.2rem;">🤖</div>`;
        } else if (data.avatar_url) {
            avatarHTML = `<img src="${data.avatar_url}" alt="${this.escapeHtml(senderName)}" class="rounded-circle object-fit-cover shadow-sm" width="38" height="38">`;
        } else {
            const initialChar = senderName ? senderName.charAt(0).toUpperCase() : 'U';
            avatarHTML = `<div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 38px; height: 38px;">${initialChar}</div>`;
        }

        let myAvatarHTML = '';
        if (!data.is_ai && isMe) {
            if (window.currentUserAvatarUrl) {
                myAvatarHTML = `<div class="flex-shrink-0 ms-2"><img src="${window.currentUserAvatarUrl}" alt="${this.escapeHtml(senderName)}" class="rounded-circle object-fit-cover shadow-sm" width="38" height="38"></div>`;
            } else {
                const initialChar = senderName ? senderName.charAt(0).toUpperCase() : 'U';
                myAvatarHTML = `<div class="flex-shrink-0 ms-2"><div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 38px; height: 38px;">${initialChar}</div></div>`;
            }
        }

        messageDiv.innerHTML = `
            ${data.is_ai || !isMe ? `<div class="flex-shrink-0 me-2">${avatarHTML}</div>` : ''}
            <div class="message-bubble-wrapper position-relative" style="max-width: 70%;">
                
                <div class="message-hover-toolbar position-absolute shadow bg-white border rounded-pill px-3 py-1 d-flex gap-2 align-items-center ${toolbarPosition}"
                    style="top: -22px; display: none; z-index: 10; font-size: 0.85rem;">
                    <span class="cursor-pointer text-secondary hover-scale" onclick="prepareReplyMessage('${messageId}')" title="Trả lời tin nhắn này">
                        <i class="fas fa-reply"></i>
                    </span>
                    <span class="border-start mx-1"></span>
                    <span class="cursor-pointer text-primary hover-scale fw-bold d-flex align-items-center gap-1" onclick="promoteMessageToKnowledge('${messageId}')" title="Đưa tin nhắn này vào kho tri thức nhóm">
                        <i class="fas fa-graduation-cap"></i> Học 🧠
                    </span>
                    <span class="border-start mx-1"></span>
                    <span class="cursor-pointer text-success hover-scale" onclick="handleFeedback('${messageId}', 'like')" title="Thích">
                        <i class="far fa-thumbs-up"></i>
                    </span>
                    <span class="cursor-pointer text-danger hover-scale" onclick="handleFeedback('${messageId}', 'heart')" title="Thả tim">
                        <i class="far fa-heart"></i>
                    </span>
                    <span class="cursor-pointer text-muted hover-scale" onclick="handleFeedback('${messageId}', 'dislike')" title="Không thích">
                        <i class="far fa-thumbs-down"></i>
                    </span>
                </div>

                <div class="card shadow-sm position-relative ${cardClass}">
                    <div class="card-header py-1 px-3 small d-flex justify-content-between align-items-center ${headerBoxClass}">
                        <span class="me-3"><strong>${data.is_ai ? '🤖 AI Assistant' : this.escapeHtml(senderName)}</strong></span>
                        <span class="text-secondary opacity-75" style="font-size: 0.75rem;">${timeString}</span>
                    </div>
                    <div class="card-body py-2 px-3">
                        ${replyQuoteHTML}
                        <p class="message-content-text mb-0 text-break whitespace-pre-wrap">${formattedContent}</p>
                    </div>
                </div>
            </div>
            ${!data.is_ai && isMe ? myAvatarHTML : ''}
        `;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /**
     * Tự động cuộn khung chat xuống vị trí tin nhắn mới nhất một cách chính xác.
     */
    scrollToBottom() {
        const messagesContainer = document.getElementById('message-list-container');
        if (!messagesContainer) return;

        const executeScroll = () => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        };

        requestAnimationFrame(() => {
            executeScroll();
            setTimeout(executeScroll, 50);
            setTimeout(executeScroll, 150);
            setTimeout(executeScroll, 300);
        });
    }

    /**
     * Chống XSS an toàn cho chuỗi văn bản HTML.
     * @param {string} text - Văn bản đầu vào cần làm sạch.
     * @returns {string} Chuỗi văn bản đã được escape an toàn.
     */
    escapeHtml(text) {
        if (!text) return '';
        return text
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

/**
 * Hàm khởi tạo toàn cục kích hoạt hệ thống WebSocket theo nhóm (Group-Centric).
 */
function initWebSocket() {
    if (!window.chatWs) {
        window.chatWs = new ChatWebSocketClient();
        console.log("[ChatWebSocketClient] Đã kích hoạt hệ thống WebSocket độc lập.");
    }

    if (window.chatWs && typeof window.chatWs.scrollToBottom === 'function') {
        window.chatWs.scrollToBottom();
    }
}

/**
 * Quét chuỗi nội dung tin nhắn và tự động chuyển đổi các thẻ @username thành badge chữ xanh.
 * @param {string} text - Nội dung tin nhắn thô.
 * @returns {string} - Chuỗi HTML đã được làm đẹp.
 */
function formatMessageMentions(text) {
    if (!text) return "";
    // Sử dụng Regular Expression tìm kiếm chuỗi bắt đầu bằng @ theo sau là ký tự chữ/số
    const mentionRegex = /@([a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]+)/g;
    return text.replace(mentionRegex, '<span class="badge bg-primary-subtle text-primary fw-bold px-1 rounded">@$1</span>');
}