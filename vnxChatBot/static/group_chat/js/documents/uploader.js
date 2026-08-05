/**
 * File: static/group_chat/js/documents/uploader.js
 * Mục đích: Quản lý tính năng upload tài liệu vào nhóm chat qua cả hai hình thức: 
 *           Kéo thả (DropZone) và Chọn file truyền thống qua Input File, 
 *           đồng thời kích hoạt pipeline xử lý (FileProcessor -> VectorStore) theo Group-Centric.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 */

class DocumentUploader {
    /**
     * Khởi tạo Uploader cho một nhóm cụ thể.
     * @param {string|number} groupId - ID định danh của nhóm.
     * @param {string} dropZoneId - ID của HTML element dùng làm vùng kéo thả file.
     */
    constructor(groupId, dropZoneId) {
        this.groupId = groupId;
        this.dropZoneId = dropZoneId;
        this.dropZone = document.getElementById(dropZoneId);
        this.initEvents();
        this.initFileInputEvent(); // Bổ sung lắng nghe sự kiện chọn file qua thẻ input
    }

    /**
     * Gắn các sự kiện kéo thả file vào vùng dropZone.
     */
    initEvents() {
        if (!this.dropZone) {
            console.warn(`[Uploader] ⚠️ Không tìm thấy phần tử dropZone với ID: ${this.dropZoneId}. Uploader sẽ chuyển sang chế độ chờ.`);
            return;
        }

        // Ngăn chặn hành vi mặc định của trình duyệt khi kéo file
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        // Xử lý sự kiện thả file vào vùng chỉ định
        this.dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                this.handleFiles(files);
            }
        }, false);
    }

    /**
     * Đăng ký sự kiện lắng nghe từ thẻ input chọn file thông thường (nếu có trên giao diện).
     */
    initFileInputEvent() {
        const fileInput = document.getElementById('document-file-input') || document.querySelector('input[type="file"]');
        if (!fileInput) {
            console.info("[Uploader] ℹ️ Không tìm thấy input[type='file'] trên giao diện. Chỉ sử dụng chế độ kéo thả.");
            return;
        }

        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                this.handleFiles(files);
                // Reset lại input để có thể chọn lại chính file đó lần sau nếu cần
                e.target.value = '';
            }
        });
    }

    /**
     * Xử lý danh sách file được chọn và gửi lên server theo định hướng Group-Centric.
     * @fn Pipeline: FileProcessor -> VectorStore tự động kích hoạt ở Backend.
     * @param {FileList} files - Danh sách các file người dùng cung cấp.
     */
    async handleFiles(files) {
        if (files.length === 0) return;

        const formData = new FormData();
        // Phải dùng key là 'file' để khớp với request.FILES.get('file') ở Django view
        for (let i = 0; i < files.length; i++) {
            formData.append('file', files[i]);
        }
        formData.append('group_id', this.groupId);

        try {
            console.log(`📤 [Uploader] Đang tải lên ${files.length} file vào nhóm ID: ${this.groupId}`);

            // Khớp chính xác với đường dẫn URL: /groups/<group_id>/documents/upload/
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
                alert("🎉 " + result.message);
            } else {
                console.error("[Uploader] ❌ Lỗi từ server:", result);
                alert("❌ Tải lên thất bại: " + (result.message || result.error || 'Lỗi không xác định'));
            }
        } catch (error) {
            console.error("[Uploader Error] ❌ Lỗi mạng khi upload file:", error);
            alert("❌ Đã xảy ra lỗi kết nối mạng trong quá trình tải tài liệu.");
        }
    }

    /**
     * Lấy mã CSRF Token từ cookie của Django.
     * @returns {string|null}
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
    const groupId = window.currentGroupId || chatMessagesContainer?.dataset.groupId;

    if (groupId) {
        window.documentUploader = new DocumentUploader(groupId, 'chat-messages');
        console.log("[Uploader] ✅ Khởi tạo DocumentUploader thành công cho Group ID:", groupId);
    } else {
        console.warn("[Uploader] ⚠️ Không tìm thấy Group ID hợp lệ để khởi tạo DocumentUploader.");
    }
}