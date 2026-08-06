/**
 * File: apps/group_chat/static/group_chat/js/tab/knowledge_tab.js
 * Mục đích: Xử lý các thao tác phê duyệt (approve) và rollback đơn vị tri thức (KnowledgeUnit) qua AJAX.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Lắng nghe sự kiện click nút duyệt hoặc rollback nếu dùng class chung
    document.querySelectorAll('.btn-approve-knowledge').forEach(button => {
        button.addEventListener('click', function () {
            const knowledgeId = this.getAttribute('data-id');
            approveKnowledge(knowledgeId);
        });
    });
});

/**
 * Gửi yêu cầu AJAX phê duyệt KnowledgeUnit
 * @param {number|string} knowledgeId - ID của đơn vị kiến thức cần duyệt
 */
function approveKnowledge(knowledgeId) {
    if (!confirm('Bạn có chắc chắn muốn phê duyệt đơn vị tri thức này đưa vào Vector DB?')) {
        return;
    }

    // Lấy group_id từ thuộc tính data hoặc URL hiện tại
    const currentPath = window.location.pathname; // Ví dụ: /groups/15/
    const match = currentPath.match(/\/groups\/(\d+)\//);
    if (!match) {
        alert('❌ Không xác định được mã nhóm (group_id).');
        return;
    }
    const groupId = match[1];

    const url = `/groups/${groupId}/knowledge/${knowledgeId}/action/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ action: 'approve' })
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
                alert("✅ " + (data.message || 'Phê duyệt tri thức thành công!'));
                location.reload(); // Tải lại trang để cập nhật trạng thái mới
            } else {
                alert("⚠️ " + (data.message || 'Không thể phê duyệt tri thức.'));
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