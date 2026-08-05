/**
 * File: apps/group_chat/static/group_chat/js/replay_messages.js
 * Mục đích: Quản lý kết nối WebSocket thời gian thực, xử lý gửi/nhận tin nhắn đa luồng, 
 *          tính năng Reply trích dẫn kiểu Zalo, và Feedback Loop cho Group-Centric Workspace.
 * Tác giả: Kỹ sư trưởng vnxChatBot Architecture Team
 * Module liên kết: apps.group_chat (Consumer & Templates)
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Khởi tạo kết nối WebSocket an toàn theo Group ID từ thuộc tính DOM
    const chatMessagesContainer = document.getElementById('chat-messages');
    if (!chatMessagesContainer) return;

    const groupId = chatMessagesContainer.getAttribute('data-group-id');
    const wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";

    // Khởi tạo biến toàn cục window.chatSocket và hàng đợi tin nhắn chờ (message queue) nếu chưa có
    if (typeof window.chatSocket === 'undefined' || !window.chatSocket || window.chatSocket.readyState === WebSocket.CLOSED) {
        window.chatSocket = new WebSocket(
            wsScheme + window.location.host + '/ws/groups/' + groupId + '/'
        );
        window.chatMessageQueue = []; // Hàng đợi chứa các gói tin gửi đi khi socket đang handshake
    }

    /**
     * Sự kiện: Khi WebSocket kết nối thành công (OPEN)
     * Tự động flush (xả) các tin nhắn nằm trong hàng đợi chờ gửi đi trước đó.
     */
    window.chatSocket.onopen = function (e) {
        console.log("🟢 [WebSocket] Kết nối thời gian thực thành công tới Group ID:", groupId);
        if (window.chatMessageQueue && window.chatMessageQueue.length > 0) {
            while (window.chatMessageQueue.length > 0) {
                const pendingMessage = window.chatMessageQueue.shift();
                window.chatSocket.send(JSON.stringify(pendingMessage));
            }
        }
    };

    // 2. Xử lý sự kiện nhận tin nhắn từ WebSocket Server (Real-time Broadcast)
    window.chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);

        const isMe = data.sender_name === window.currentUsername;
        const messageDiv = document.createElement('div');

        messageDiv.className = `d-flex ${data.is_ai || !isMe ? 'justify-content-start' : 'justify-content-end'} mb-3 message-item position-relative`;
        messageDiv.setAttribute('data-message-id', data.message_id);

        let cardClass = data.is_ai ? 'vnx-ai-message-card' : (isMe ? 'vnx-user-message-card' : 'vnx-other-message-card');
        let headerBoxClass = data.is_ai ? 'vnx-ai-header-box' : (isMe ? 'vnx-user-header-box' : 'vnx-other-header-box');
        const timeString = data.created_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Xử lý trích dẫn Reply (Zalo-style Quote) nếu có
        let replyQuoteHTML = '';
        if (data.reply_to) {
            replyQuoteHTML = `
                <div class="bg-light border-start border-secondary border-3 p-2 mb-2 rounded-end small text-muted">
                    <strong>${data.reply_to.sender_name}:</strong>
                    <p class="mb-0 text-truncate">${data.reply_to.content}</p>
                </div>
            `;
        }

        // Xử lý hiển thị Avatar linh hoạt (AI / User Profile Image / Fallback Initials)
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

        messageDiv.innerHTML = `
            ${data.is_ai || !isMe ? `<div class="flex-shrink-0 me-2">${avatarHTML}</div>` : ''}
            <div class="message-bubble-wrapper position-relative" style="max-width: 70%;">
                <div class="card shadow-sm position-relative ${cardCard ? cardCard : cardClass}">
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

        chatMessagesContainer.appendChild(messageDiv);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    };

    window.chatSocket.onclose = function (e) {
        console.warn('⚠️ [WebSocket] Kênh kết nối đã đóng. Đang thử kết nối lại...');
    };

    // 3. Quản lý trạng thái Reply tin nhắn
    window.currentReplyToId = null;

    window.prepareReplyMessage = function (messageId, senderName, messageContent) {
        window.currentReplyToId = messageId;
        const previewBar = document.getElementById('reply-preview-bar');
        const usernameSpan = document.getElementById('reply-to-username');
        const contentP = document.getElementById('reply-to-content');

        if (previewBar && usernameSpan && contentP) {
            usernameSpan.textContent = senderName;
            contentP.textContent = messageContent;
            previewBar.classList.remove('d-none');
            previewBar.classList.add('d-flex');
        }

        const chatInput = document.getElementById('chat-message-input');
        if (chatInput) chatInput.focus();
    };

    window.cancelReply = function () {
        window.currentReplyToId = null;
        const previewBar = document.getElementById('reply-preview-bar');
        if (previewBar) {
            previewBar.classList.remove('d-flex');
            previewBar.classList.add('d-none');
        }
    };

    // 4. Xử lý sự kiện gửi tin nhắn qua form chat và nút bấm
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-message-input');
    const chatSubmitBtn = document.getElementById('chat-message-submit');

    if (chatForm && chatInput) {
        chatForm.onsubmit = function (e) {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (!message) return;

            const payload = {
                'message': message,
                'reply_to_id': window.currentReplyToId
            };

            // Kiểm tra trạng thái WebSocket: Nếu đã sẵn sàng thì gửi ngay, nếu đang CONNECTING thì đẩy vào hàng đợi
            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {
                window.chatSocket.send(JSON.stringify(payload));
                chatInput.value = '';
                window.cancelReply();
            } else if (window.chatSocket && window.chatSocket.readyState === WebSocket.CONNECTING) {
                console.warn("⏳ [WebSocket] Kênh đang thiết lập kết nối, tin nhắn được đưa vào hàng đợi tạm thời.");
                if (!window.chatMessageQueue) window.chatMessageQueue = [];
                window.chatMessageQueue.push(payload);
                chatInput.value = '';
                window.cancelReply();
            } else {
                console.error("❌ [WebSocket] Lỗi kết nối: Không thể gửi tin nhắn vì socket ở trạng thái CLOSED/CLOSING.");
                alert("Kết nối WebSocket chưa sẵn sàng. Vui lòng tải lại trang (F5).");
            }
        };
    }

    if (chatSubmitBtn && chatInput) {
        chatSubmitBtn.onclick = function (e) {
            e.preventDefault();
            if (chatForm) {
                chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        };
    }
});