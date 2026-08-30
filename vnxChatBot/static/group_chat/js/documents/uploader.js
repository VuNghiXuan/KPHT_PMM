/**
 * File: static/group_chat/js/documents/uploader.js
 * Mục đích: Quản lý tính năng upload tài liệu vào nhóm chat qua cả hai hình thức: 
 *           Kéo thả (DropZone) và Chọn file truyền thống qua Input File, 
 *           đồng thời kích hoạt pipeline xử lý và tự động render tin nhắn file lên giao diện chat trực tiếp.
 * Tác giả: Kỹ sư phần mềm cao cấp vnxChatBot
 */

class DocumentUploader {
    /**
     * Khởi tạo Uploader cho một nhóm cụ thể.
     * @param {string|number} groupId - ID định danh của nhóm (Group-Centric).
     * @param {string} dropZoneId - ID của HTML element dùng làm vùng kéo thả file.
     */
    constructor(groupId, dropZoneId) {
        this.groupId = groupId;
        this.dropZoneId = dropZoneId;
        this.dropZone = document.getElementById(dropZoneId);
        this.initEvents();
        this.initFileInputEvent();
    }

    /**
     * Gắn các sự kiện kéo thả file vào vùng dropZone, ngăn chặn hành vi mặc định của trình duyệt.
     */
    initEvents() {
        if (!this.dropZone) {
            console.warn(`[Uploader] ⚠️ Không tìm thấy phần tử dropZone với ID: ${this.dropZoneId}.`);
            return;
        }

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        this.dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                this.handleFiles(files);
            }
        }, false);
    }

    /**
     * Đăng ký sự kiện lắng nghe từ thẻ input chọn file thông thường.
     */
    initFileInputEvent() {
        const fileInput = document.getElementById('document-file-input') || document.querySelector('input[type="file"]');
        if (!fileInput) {
            console.info("[Uploader] ℹ️ Không tìm thấy input[type='file'] trên giao diện.");
            return;
        }

        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                this.handleFiles(files);
                e.target.value = ''; // Reset input để cho phép chọn lại cùng một file nếu cần
            }
        });
    }

    /**
     * Xử lý danh sách file được chọn và gửi lên server theo định hướng Group-Centric.
     * @param {FileList} files - Danh sách các file người dùng cung cấp.
     */
    async handleFiles(files) {
        if (files.length === 0) return;

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('file', files[i]);
        }
        formData.append('group_id', this.groupId);

        try {
            console.log(`📤 [Uploader] Đang tải lên ${files.length} file vào nhóm ID: ${this.groupId}`);

            const response = await fetch(`/groups/${this.groupId}/upload/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });

            const result = await response.json();
            if (response.ok && result.status === 'success') {
                console.log("[Uploader] ✅ Tải lên file thành công:", result);

                // 🔄 [UI Update]: Cập nhật giao diện chat trực tiếp thông qua WebSocket client hoặc DOM injection
                this.refreshChatInterface(result);

            } else {
                console.error("[Uploader] ❌ Lỗi từ server:", result);
                alert("❌ Tải lên thất bại: " + (result.message || result.error || 'Lỗi không xác định'));
            }
        } catch (error) {
            console.error("[Uploader Error] ❌ Lỗi kết nối mạng khi upload file:", error);
            alert("❌ Đã xảy ra lỗi kết nối mạng trong quá trình tải tài liệu.");
        }
    }

    /**
     * Cập nhật giao diện chat sau khi upload thành công mà không cần tải lại trang (F5).
     * @param {Object} result - Dữ liệu JSON trả về từ server chứa thông tin file và HTML fragment.
     */
    refreshChatInterface(result) {
        const chatMessages = document.getElementById('chat-messages') || document.getElementById('chat-messages-container');

        if (result.html && chatMessages) {
            chatMessages.insertAdjacentHTML('beforeend', result.html);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            console.log("[Uploader] ✅ Đã render thành công message item HTML từ server.");
            return;
        }

        if (window.chatWs && typeof window.chatWs.appendMessage === 'function') {
            const messageData = {
                sender_name: window.currentUsername || 'Bạn',
                is_ai: false,
                content: `📁 Đã tải lên tài liệu: **${result.file_name || 'Tài liệu mới'}**`,
                created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                message_id: result.message_id || Date.now()
            };
            window.chatWs.appendMessage(messageData);
            return;
        }

        if (chatMessages) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'd-flex justify-content-end mb-3 message-item';
            messageDiv.innerHTML = `
                <div class="card shadow-sm vnx-user-message-card" style="max-width: 70%;">
                    <div class="card-body py-2 px-3">
                        <p class="mb-2 text-break">📁 Đã tải lên tài liệu thành công: <strong>${result.file_name || 'Tài liệu mới'}</strong></p>
                        <a href="${result.file_url || '#'}" download class="btn btn-sm btn-outline-primary py-1 px-2">
                            <i class="fas fa-download"></i> Tải xuống
                        </a>
                    </div>
                </div>
            `;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            console.warn("[Uploader] ⚠️ Không tìm thấy khung chứa tin nhắn để render trực tiếp.");
        }
    }

    /**
     * Lấy mã CSRF Token từ cookie của Django để bảo mật request POST.
     * @returns {string|null} - Giá trị CSRF token hoặc null nếu không tìm thấy.
     */
    getCsrfToken() {
        let cookieValue = null;
        const name = 'csrftoken';
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }
}

/**
 * Hàm khởi tạo toàn cục được gọi từ main.js để kích hoạt tính năng upload tài liệu.
 */
function initDocumentUploader() {
    const chatMessagesContainer = document.getElementById('chat-messages');

    // 🔍 Quét tìm groupId từ nhiều nguồn dự phòng khác nhau để tránh lỗi undefined
    let groupId = window.currentGroupId || chatMessagesContainer?.dataset.groupId;

    if (!groupId) {
        // Fallback: Tự động bóc tách group_id từ URL hiện tại (ví dụ: /groups/5/workspace/)
        const match = window.location.pathname.match(/\/groups\/(\d+)\//);
        if (match && match[1]) {
            groupId = match[1];
            console.info("[Uploader] ℹ️ Lấy groupId tự động từ URL pathname:", groupId);
        }
    }

    if (groupId) {
        window.documentUploader = new DocumentUploader(groupId, 'chat-messages');
        console.log("[Uploader] ✅ Khởi tạo DocumentUploader thành công cho Group ID:", groupId);
    } else {
        console.warn("[Uploader] ⚠️ Không tìm thấy Group ID hợp lệ để khởi tạo DocumentUploader.");
    }
}