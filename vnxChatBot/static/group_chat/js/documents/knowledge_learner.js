/**
 * File: static/group_chat/js/documents/knowledge_learner.js
 * Mô tả: Xử lý kích hoạt AI học tập cho tài liệu với cơ chế lập trình hướng đối tượng.
 * Tuân thủ bảo mật Django CSRF và chuẩn Modular Monolith.
 */
class KnowledgeLearner {
    constructor() {
        console.log("📚 [KnowledgeLearner] Khởi tạo mô-đun thành công.");
        this.initEventListeners();
    }

    getCsrfToken() {
        // 🛡️ [Security]: Ưu tiên lấy từ input ẩn chuẩn Django {% csrf_token %}
        const inputToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
        if (inputToken) return inputToken;

        // Fallback sang thẻ Meta nếu có
        const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (metaToken) return metaToken;

        // Fallback cuối cùng: Đọc từ Cookie của trình duyệt
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith('csrftoken=')) {
                    cookieValue = decodeURIComponent(cookie.substring('csrftoken='.length));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async triggerLearning(groupId, documentId) {
        const csrfToken = this.getCsrfToken();
        const apiUrl = `/groups/${groupId}/documents/${documentId}/learn/`;

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                }
            });

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error(`Server trả về lỗi HTTP ${response.status} (Kiểm tra lại quyền hạn hoặc đường dẫn API).`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                alert("🚀 Kích hoạt AI học tập thành công!");
                location.reload();
            } else {
                alert("⚠️ Lỗi: " + (data.message || 'Không thể kích hoạt.'));
            }
        } catch (error) {
            console.error('❌ [Knowledge Learner Error]:', error.message);
            alert('❌ Lỗi kết nối đến máy chủ: ' + error.message);
        }
    }

    initEventListeners() {
        document.body.addEventListener('click', (event) => {
            const btn = event.target.closest('.btn-ai-learn');
            if (btn) {
                const documentId = btn.getAttribute('data-doc-id');
                // 🎯 [Single Source of Truth]: Đồng bộ định danh container chứa group_id theo chuẩn giao diện nhóm
                const chatContainer = document.getElementById('message-list-container') || document.querySelector('[data-group-id]');
                const groupId = chatContainer ? chatContainer.getAttribute('data-group-id') : null;

                if (groupId && documentId) {
                    this.triggerLearning(groupId, documentId);
                } else {
                    console.error("❌ Không tìm thấy groupId hoặc documentId.");
                }
            }
        });
    }
}

// 🚀 Tự động khởi tạo mô-đun khi trang tải xong
document.addEventListener('DOMContentLoaded', () => {
    window.knowledgeLearnerInstance = new KnowledgeLearner();
});