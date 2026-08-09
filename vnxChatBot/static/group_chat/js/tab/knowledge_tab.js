/**
 * File: apps/group_chat/static/group_chat/js/tab/knowledge_tab.js
 * Mục đích: Xử lý các thao tác phê duyệt (approve), từ chối (reject), rollback và xem chi tiết (inspect) đơn vị tri thức qua AJAX.
 * Tác giả: Kiến trúc sư VnxChatBot
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Lắng nghe sự kiện click nút Duyệt (cả ngoài danh sách và trong Modal)
    document.querySelectorAll('.btn-approve-knowledge').forEach(button => {
        button.addEventListener('click', function () {
            const knowledgeId = this.getAttribute('data-id');
            handleKnowledgeAction(knowledgeId, 'approve', 'Bạn có chắc chắn muốn phê duyệt đơn vị tri thức này đưa vào Vector DB?');
        });
    });

    // 2. Lắng nghe sự kiện click nút Hủy / Từ chối
    document.querySelectorAll('.btn-reject-knowledge').forEach(button => {
        button.addEventListener('click', function () {
            const knowledgeId = this.getAttribute('data-id');
            handleKnowledgeAction(knowledgeId, 'reject', 'Bạn có chắc muốn từ chối tài liệu này không?');
        });
    });

    // 3. Lắng nghe sự kiện click nút Gỡ/Rollback tri thức đã duyệt
    document.querySelectorAll('.btn-rollback-knowledge').forEach(button => {
        button.addEventListener('click', function () {
            const knowledgeId = this.getAttribute('data-id');
            handleKnowledgeAction(knowledgeId, 'reject', 'Bạn có chắc muốn gỡ tài liệu này khỏi Vector DB (Rollback)?');
        });
    });

    // 4. Lắng nghe sự kiện click nút Học AI (AILearn)
    document.querySelectorAll('.btn-ai-learn').forEach(button => {
        button.addEventListener('click', function () {
            const documentId = this.getAttribute('data-document-id');
            triggerAILearn(documentId);
        });
    });

    // 5. Lắng nghe sự kiện mở Modal Chi Tiết (Smart Staging Inspection)
    const knowledgeDetailModal = document.getElementById('knowledgeDetailModal');
    if (knowledgeDetailModal) {
        knowledgeDetailModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget; // Nút kích hoạt modal

            // Lấy data attributes từ button
            const knowledgeId = button.getAttribute('data-id');
            const fileName = button.getAttribute('data-filename');
            const entityName = button.getAttribute('data-entity');
            const content = button.getAttribute('data-content');

            // Đổ dữ liệu vào các phần tử tương ứng trong Modal
            document.getElementById('modal-file-name').textContent = fileName || 'Không có tên';
            document.getElementById('modal-entity-name').textContent = entityName || 'Chưa xác định';
            document.getElementById('modal-content-preview').textContent = content || 'Không có nội dung trích xuất.';

            // Gán ID cho các nút hành động bên trong footer của Modal
            document.getElementById('modal-btn-approve').setAttribute('data-id', knowledgeId);
            document.getElementById('modal-btn-reject').setAttribute('data-id', knowledgeId);

            // Mô phỏng / load các câu hỏi gợi ý (có thể mở rộng gọi API riêng nếu cần)
            const queryList = document.getElementById('modal-suggested-queries');
            queryList.innerHTML = `
                <li>Tài liệu liên quan trực tiếp đến thực thể: <strong>${entityName}</strong></li>
                <li>Hệ thống sẵn sàng đưa vào RAG sau khi Admin xác nhận kiểm duyệt thủ công.</li>
            `;
        });
    }
});

/**
 * Hàm chung xử lý gọi AJAX cho các hành động phê duyệt hoặc từ chối tri thức
 * @param {number|string} knowledgeId - ID của KnowledgeUnit
 * @param {string} action - Hành động ('approve' hoặc 'reject')
 * @param {string} confirmMessage - Câu hỏi xác nhận trước khi thực thi
 */
function handleKnowledgeAction(knowledgeId, action, confirmMessage) {
    if (!knowledgeId) {
        alert('❌ Không tìm thấy ID định danh của tri thức.');
        return;
    }

    if (!confirm(confirmMessage)) {
        return;
    }

    const currentPath = window.location.pathname;
    const match = currentPath.match(/\/groups\/(\d+)\//);
    if (!match) {
        alert('❌ Không xác định được mã nhóm (group_id).');
        return;
    }
    const groupId = match[1];

    // Khớp với URL pattern backend
    const url = `/groups/${groupId}/knowledge/${knowledgeId}/${action}/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(async response => {
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error(`Server trả về mã lỗi HTTP ${response.status}`);
            }
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Lỗi hệ thống.');
            return data;
        })
        .then(data => {
            if (data.status === 'success' || data.success) {
                alert("✅ " + (data.message || 'Xử lý tri thức thành công!'));
                location.reload();
            } else {
                alert("⚠️ " + (data.message || 'Không thể thực hiện hành động này.'));
            }
        })
        .catch(error => {
            alert('❌ Lỗi kết nối hoặc xử lý: ' + error.message);
        });
}

/**
 * Hàm kích hoạt AI học tài liệu và cập nhật giao diện
 */
function triggerAILearn(documentId) {
    const url = `/groups/documents/${documentId}/ai-learn/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(async response => {
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error(`Server trả về mã lỗi HTTP ${response.status}`);
            }
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Lỗi hệ thống.');
            return data;
        })
        .then(data => {
            if (data.status === 'success') {
                alert("🧠 " + (data.message || 'Tài liệu đã được AI tiếp thu thành công!'));
                location.reload();
            } else {
                alert("⚠️ " + (data.message || 'Không thể xử lý tài liệu.'));
            }
        })
        .catch(error => {
            alert('❌ Lỗi kết nối hoặc xử lý: ' + error.message);
        });
}

/**
 * Hàm lấy giá trị CSRF Token từ Cookie chuẩn Django
 */
function getCookie(name) {
    let cookieValue = null;
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
    return cookieValue;
}