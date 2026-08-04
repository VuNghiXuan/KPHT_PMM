/**
 * File: static/group_chat/js/func_for_group_detail.js
 * Mục đích: Quản lý kết nối WebSocket thời gian thực, xử lý hiển thị tin nhắn chat chung giữa các thành viên
 *           phân lập theo group_id, hiển thị phản hồi từ AI, tích hợp Feedback Loop 
 *           cùng tiến trình xử lý FileProcessor qua sự kiện Upload.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Lấy vùng chứa tin nhắn (nơi đặt các thuộc tính data-* cấu hình tenant)
    const chatMessagesContainer = document.getElementById('chat-messages');
    if (!chatMessagesContainer) return;

    // Đọc giá trị group_id, tên người dùng hiện tại và mã xác thực chống giả mạo từ attribute HTML
    const groupId = chatMessagesContainer.dataset.groupId;
    const currentUsername = chatMessagesContainer.dataset.currentUsername;
    const csrfToken = chatMessagesContainer.dataset.csrfToken;

    // Kiểm tra an toàn tránh lỗi kết nối nếu thiếu group id (Bảo đảm nguyên tắc Group-Centric)
    if (!groupId || groupId === 'undefined') {
        console.error("❌ Lỗi: Không tìm thấy Group ID hợp lệ cho WebSocket!");
        return;
    }

    // Thiết lập giao thức kết nối WebSocket thời gian thực (WSS cho HTTPS hoặc WS cho HTTP)
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const chatSocket = new WebSocket(`${wsScheme}://${window.location.host}/ws/groups/${groupId}/`);

    /**
     * Lắng nghe tin nhắn real-time từ WebSocket Server.
     * Đã chuẩn hóa hiển thị Avatar (hình ảnh thực tế hoặc chữ cái dự phòng).
     */
    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        const chatMessages = document.getElementById('chat-messages');

        const isMe = data.sender_name === currentUsername;
        const messageDiv = document.createElement('div');

        // 1. Phân định vị trí hiển thị trái / phải (Tenant / Sender Isolation)
        messageDiv.className = `d-flex ${data.is_ai || !isMe ? 'justify-content-start' : 'justify-content-end'} mb-3 message-item position-relative`;
        messageDiv.setAttribute('data-message-id', data.message_id);

        // 2. Xác định class màu sắc card và header box
        let cardClass = '';
        let headerBoxClass = '';
        let toolbarPosition = isMe && !data.is_ai ? 'toolbar-left' : 'toolbar-right';

        if (data.is_ai) {
            cardClass = 'vnx-ai-message-card';
            headerBoxClass = 'vnx-ai-header-box';
        } else if (isMe) {
            cardClass = 'vnx-user-message-card';
            headerBoxClass = 'vnx-user-header-box';
        } else {
            cardClass = 'vnx-other-message-card';
            headerBoxClass = 'vnx-other-header-box';
        }

        const timeString = data.created_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // 3. Logic render Avatar thông minh (Kiểm tra xem có ảnh avatar_url thật hay không)
        let avatarHTML = '';
        if (data.is_ai) {
            avatarHTML = `
            <div class="rounded-circle bg-info text-white d-flex align-items-center justify-content-center shadow-sm"
                style="width: 38px; height: 38px; font-size: 1.2rem;">🤖</div>
        `;
        } else if (data.avatar_url) {
            // Nếu có đường dẫn ảnh avatar từ profile user
            avatarHTML = `
            <img src="${data.avatar_url}" alt="${data.sender_name}"
                class="rounded-circle object-fit-cover shadow-sm" width="38" height="38">
        `;
        } else {
            // Fallback: Hiển thị chữ cái đầu nếu chưa có ảnh
            avatarHTML = `
            <div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm"
                style="width: 38px; height: 38px;">${data.sender_name.charAt(0).toUpperCase()}</div>
        `;
        }

        // Riêng user đang đăng nhập (isMe) thì dùng avatar của chính họ (nếu có)
        let myAvatarHTML = '';
        if (!data.is_ai && isMe) {
            // Lấy avatar của current user (có thể lưu biến toàn cục currentAvatarUrl từ template Django ra)
            if (typeof currentUserAvatarUrl !== 'undefined' && currentUserAvatarUrl) {
                myAvatarHTML = `
                <div class="flex-shrink-0 ms-2">
                    <img src="${currentUserAvatarUrl}" alt="${data.sender_name}"
                        class="rounded-circle object-fit-cover shadow-sm" width="38" height="38">
                </div>
            `;
            } else {
                myAvatarHTML = `
                <div class="flex-shrink-0 ms-2">
                    <div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm"
                        style="width: 38px; height: 38px;">${data.sender_name.charAt(0).toUpperCase()}</div>
                </div>
            `;
            }
        }

        // 4. Dựng cấu trúc HTML hoàn chỉnh
        messageDiv.innerHTML = `
        ${data.is_ai || !isMe ? `<div class="flex-shrink-0 me-2">${avatarHTML}</div>` : ''}

        <div class="message-bubble-wrapper position-relative" style="max-width: 70%;">

            <!-- Thanh công cụ nổi thông minh (Hover Action Menu kiểu Zalo) -->
            <div class="message-hover-toolbar position-absolute shadow bg-white border rounded-pill px-3 py-1 d-flex gap-2 align-items-center ${toolbarPosition}"
                style="top: -22px; display: none; z-index: 10; font-size: 0.85rem;">

                <span class="cursor-pointer text-secondary hover-scale"
                    onclick="prepareReplyMessage('${data.message_id}', '${data.is_ai ? 'AI Assistant' : data.sender_name}')"
                    title="Trả lời tin nhắn này">
                    <i class="fas fa-reply"></i>
                </span>
                <span class="border-start mx-1"></span>

                <span class="cursor-pointer text-primary hover-scale fw-bold d-flex align-items-center gap-1"
                    onclick="promoteMessageToKnowledge('${data.message_id}')" title="Đưa tin nhắn này vào kho tri thức nhóm">
                    <i class="fas fa-graduation-cap"></i> Học 🧠
                </span>

                <span class="border-start mx-1"></span>
                <span class="cursor-pointer text-success hover-scale" onclick="handleFeedback('${data.message_id}', 'like')" title="Thích">
                    <i class="far fa-thumbs-up"></i>
                </span>
                <span class="cursor-pointer text-danger hover-scale" onclick="handleFeedback('${data.message_id}', 'heart')" title="Thả tim">
                    <i class="far fa-heart"></i>
                </span>
                <span class="cursor-pointer text-muted hover-scale" onclick="handleFeedback('${data.message_id}', 'dislike')" title="Không thích">
                    <i class="far fa-thumbs-down"></i>
                </span>
            </div>

            <!-- Khung Card chính -->
            <div class="card shadow-sm position-relative ${cardClass}">
                <div class="card-header py-1 px-3 small d-flex justify-content-between align-items-center ${headerBoxClass}">
                    <span class="me-3">
                        <strong>${data.is_ai ? '🤖 AI Assistant' : data.sender_name}</strong>
                    </span>
                    <span class="text-secondary opacity-75" style="font-size: 0.75rem;">
                        ${timeString}
                    </span>
                </div>
                <div class="card-body py-2 px-3">
                    <p class="mb-0 text-break">${data.content}</p>
                </div>
            </div>
        </div>

        ${!data.is_ai && isMe ? myAvatarHTML : ''}
    `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    /**
     * Sự kiện: Xử lý submit khung nhập văn bản chat để gửi dữ liệu lên kênh WebSocket.
     */
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.onsubmit = function (e) {
            e.preventDefault();
            const inputDom = document.getElementById('chat-input');
            const message = inputDom.value.trim();
            if (message) {
                chatSocket.send(JSON.stringify({ 'message': message }));
                inputDom.value = '';
            }
        };
    }

    /**
     * Sự kiện: Lắng nghe thao tác tải lên tệp tin (Upload Document) qua FileProcessor.
     * Hiển thị trạng thái đang xử lý ngầm và tự động cuộn khung nhìn xuống thông báo.
     */
    const fileUploadInput = document.getElementById('file-upload');
    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (!file) return;

            const chatMessages = document.getElementById('chat-messages');
            const loadingDiv = document.createElement('div');
            loadingDiv.id = 'upload-loading';
            loadingDiv.className = 'd-flex justify-content-start mb-3 px-2';
            loadingDiv.innerHTML = `
                <div class="p-3 rounded-4 shadow-sm bg-white border text-primary">
                    <i class="fas fa-spinner fa-spin me-2"></i> Hệ thống đang xử lý và trích xuất tri thức từ file <b>${file.name}</b> qua FileProcessor... 🧠
                </div>
            `;
            chatMessages.appendChild(loadingDiv);

            // Tự động cuộn xuống vùng hiển thị trạng thái tải file
            chatMessages.scrollTop = chatMessages.scrollHeight;

            const formData = new FormData();
            formData.append('file', file);
            const uploadUrl = fileUploadInput.dataset.uploadUrl;

            fetch(uploadUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
                .then(response => {
                    if (document.getElementById('upload-loading')) {
                        document.getElementById('upload-loading').remove();
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        alert("✅ " + data.message);
                        location.reload();
                    } else {
                        alert('⚠️ Lỗi tải lên: ' + (data.message || 'Không thể xử lý định dạng tệp tin này.'));
                    }
                })
                .catch(error => {
                    if (document.getElementById('upload-loading')) {
                        document.getElementById('upload-loading').remove();
                    }
                    console.error('Upload Error:', error);
                    alert('❌ Đã xảy ra lỗi kết nối hoặc lỗi hệ thống ngầm trong quá trình xử lý FileProcessor.');
                });
        });
    }

    // Khởi động trang: Tự động cuộn khung chat xuống điểm thấp nhất ngay khi nạp xong nội dung lịch sử cũ
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
});

/**
 * Hàm: promoteMessageToKnowledge
 * Mục đích: Gửi yêu cầu chuyển đổi một tin nhắn thông thường thành một Đơn vị Kiến thức (KnowledgeUnit) 
 *          để nạp vào kho học tập nhóm[cite: 1].
 * @param {number|string} messageId - ID của tin nhắn cần chuyển hóa thành tri thức.
 */
function promoteMessageToKnowledge(messageId) {
    const csrfToken = document.getElementById('chat-messages')?.dataset.csrfToken || '';
    fetch(`/groups/message/${messageId}/promote-knowledge/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
        .then(res => res.json())
        .then(data => {
            alert(data.message || "Đã gửi yêu cầu cập nhật tri thức vào kho học tập nhóm!");
        })
        .catch(err => console.error('Promote Knowledge Error:', err));
}
/**
 * Xử lý thả cảm xúc và cập nhật giao diện tức thời
 * @param {string} messageId - ID của tin nhắn
 * @param {string} feedbackType - Loại cảm xúc (like, heart, dislike)
 */
function handleFeedback(messageId, feedbackType) {
    const chatContainer = document.getElementById('chat-messages');
    const csrfToken = chatContainer?.dataset.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

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
                // Tìm phần tử chứa badge cảm xúc của tin nhắn
                const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageEl) {
                    let badgeContainer = messageEl.querySelector('.reactions-badge-container');

                    // Nếu dữ liệu trả về từ server cung cấp tổng số lượng mới
                    if (data.total_count !== undefined) {
                        if (data.total_count > 0) {
                            // Nếu đã có badge, cập nhật lại số lượng
                            if (badgeContainer) {
                                const totalEl = badgeContainer.querySelector('.total-reactions-count');
                                if (totalEl) totalEl.textContent = data.total_count;
                            } else {
                                // Nếu chưa có badge nào trước đó, tải lại nhẹ partial hoặc reload trang để hiển thị khung badge
                                location.reload();
                            }
                        } else if (badgeContainer) {
                            // Nếu tổng số lượng = 0 thì ẩn badge đi
                            badgeContainer.remove();
                        }
                    }
                }
            } else {
                console.warn("⚠️ Phản hồi từ server:", data.message);
            }
        })
        .catch(error => console.error('❌ Lỗi kết nối:', error));
}

/**
 * [KNOWLEDGE & FEEDBACK LIFECYCLE]: Mở popup chi tiết danh sách người đã thả cảm xúc cho tin nhắn
 * Mục đích: 
 *   - Hiển thị danh sách chi tiết các thành viên trong nhóm đã tương tác (Like, Heart, Dislike) với một tin nhắn cụ thể.
 *   - Đồng bộ hóa dữ liệu từ API endpoint `/groups/message/<message_id>/reactions-detail/` theo định danh `group_id`.
 * Module liên kết: 
 *   - group_chat.models.MessageFeedback
 *   - group_chat.views (API xử lý trả về danh sách cảm xúc)
 * 
 * @param {string|number} messageId - ID định danh duy nhất của tin nhắn cần xem chi tiết cảm xúc.
 */
function openReactionsModal(messageId) {
    const modalBody = document.getElementById('reactionsModalBody');
    modalBody.innerHTML = '<p class="text-muted text-center small mb-0">Đang tải danh sách...</p>';

    // Khởi tạo và kích hoạt Bootstrap Modal để hiển thị giao diện tương tác
    const modal = new bootstrap.Modal(document.getElementById('reactionsDetailModal'));
    modal.show();

    // Gọi API bất đồng bộ lấy chi tiết danh sách người thả cảm xúc theo messageId
    fetch(`/groups/message/${messageId}/reactions-detail/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // [TENANT & DATA VALIDATION]: Kiểm tra trạng thái trả về và sử dụng 'data.feedbacks' khớp với Backend
            if (data.status === 'success' && data.feedbacks && data.feedbacks.length > 0) {
                let html = '<div class="d-flex flex-column gap-2">';
                data.feedbacks.forEach(item => {
                    // Sử dụng trực tiếp trường 'icon' đã được chuẩn hóa từ backend hoặc fallback theo loại phản hồi
                    let icon = item.icon || (item.type === 'like' ? '👍' : (item.type === 'heart' ? '❤️' : '👎'));
                    html += `
                    <div class="d-flex align-items-center justify-content-between reaction-detail-item">
                        <div class="d-flex align-items-center gap-2">
                            <div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 32px; height: 32px; font-size: 0.85rem;">
                                ${item.username.charAt(0).toUpperCase()}
                            </div>
                            <span class="fw-semibold text-dark small">${item.username}</span>
                        </div>
                        <span style="font-size: 1.1rem;">${icon}</span>
                    </div>
                    `;
                });
                html += '</div>';
                modalBody.innerHTML = html;
            } else {
                modalBody.innerHTML = '<p class="text-muted text-center small mb-0">Chưa có lượt tương tác nào.</p>';
            }
        })
        .catch(err => {
            console.error("Lỗi khi tải chi tiết biểu cảm:", err);
            modalBody.innerHTML = '<p class="text-danger text-center small mb-0">Không thể tải dữ liệu chi tiết.</p>';
        });
}