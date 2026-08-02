/**
 * File: static/group_chat/js/chat_workspace.js
 * Mục đích: Quản lý kết nối WebSocket thời gian thực, xử lý hiển thị tin nhắn chat chung giữa các thành viên
 *           phân lập theo group_id, hiển thị phản hồi từ AI, tích hợp Feedback Loop 
 *           cùng tiến trình xử lý FileProcessor qua sự kiện Upload.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Lấy vùng chứa tin nhắn (nơi đặt các thuộc tính data-*)
    const chatMessagesContainer = document.getElementById('chat-messages');
    if (!chatMessagesContainer) return;

    // Đọc giá trị group_id và thông tin người dùng từ attribute HTML
    const groupId = chatMessagesContainer.dataset.groupId;
    const currentUsername = chatMessagesContainer.dataset.currentUsername;
    const csrfToken = chatMessagesContainer.dataset.csrfToken;

    // Kiểm tra an toàn tránh lỗi kết nối nếu thiếu group id
    if (!groupId || groupId === 'undefined') {
        console.error("❌ Lỗi: Không tìm thấy Group ID hợp lệ cho WebSocket!");
        return;
    }

    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const chatSocket = new WebSocket(`${wsScheme}://${window.location.host}/ws/groups/${groupId}/`);

    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        const chatMessages = document.getElementById('chat-messages');

        const isMe = data.sender_name === currentUsername;
        const messageDiv = document.createElement('div');
        messageDiv.className = `d-flex ${isMe ? 'justify-content-end' : 'justify-content-start'} mb-3 px-2`;

        let aiActionsHTML = '';
        if (data.is_ai) {
            aiActionsHTML = `
                <div class="mt-2 d-flex gap-3 align-items-center pt-2 border-top border-light">
                    <i class="fas fa-thumbs-up text-success cursor-pointer" onclick="handleFeedback('${data.message_id}', 'like')" title="Thích phản hồi"></i>
                    <i class="fas fa-thumbs-down text-danger cursor-pointer" onclick="handleFeedback('${data.message_id}', 'dislike')" title="Không thích phản hồi"></i>
                    <i class="fas fa-heart text-danger cursor-pointer" onclick="handleFeedback('${data.message_id}', 'heart')" title="Yêu thích / Thả tim"></i>
                    <button class="btn btn-sm btn-outline-primary py-0 px-2 ms-auto rounded-pill" onclick="promoteMessageToKnowledge('${data.message_id}')" title="Đưa tin nhắn này vào kho tri thức nhóm">
                        <i class="fas fa-brain"></i> Học tri thức 🧠
                    </button>
                </div>
            `;
        }

        const bubbleStyle = isMe
            ? 'bg-primary text-white shadow-sm'
            : 'bg-white border shadow-sm text-dark';

        messageDiv.innerHTML = `
            <div class="p-3 rounded-4 ${bubbleStyle}" style="max-width: 75%;">
                <small class="d-block mb-1 opacity-75 fw-bold ${isMe ? 'text-white-50' : 'text-muted'}">
                    ${data.sender_name} ${data.is_ai ? '🤖' : ''}
                </small>
                <p class="mb-0 text-break" style="line-height: 1.5;">${data.content}</p>
                ${aiActionsHTML}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

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
});



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
 * Gửi phản hồi cảm xúc (Like/Dislike/Heart) của thành viên cho tin nhắn qua AJAX
 * @param {number|string} messageId - ID của tin nhắn cần tương tác
 * @param {string} feedbackType - Loại cảm xúc ('like', 'dislike', 'heart')
 */
function handleFeedback(messageId, feedbackType) {
    const csrfToken = document.getElementById('chat-messages')?.dataset.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    fetch(`/group-chat/message/${messageId}/feedback/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ type: feedbackType })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Lỗi hệ thống HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                console.log("✅ Cập nhật cảm xúc thành công:", data);
                // Tải lại trang hoặc cập nhật trực tiếp DOM phần đếm Zalo reaction
                location.reload();
            } else {
                alert("⚠️ Không thể thả cảm xúc: " + (data.message || 'Lỗi không xác định'));
            }
        })
        .catch(error => {
            console.error('❌ Lỗi kết nối hoặc xử lý feedback:', error);
            alert('Đã xảy ra lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại console.');
        });
}