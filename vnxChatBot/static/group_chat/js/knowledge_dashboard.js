/**
 * File: static/group_chat/js/knowledge_dashboard.js
 * Mô tả: Xử lý các tương tác Human-in-the-Loop và AI Power cho trang Knowledge Dashboard.
 * Chức năng: Phê duyệt, Giải quyết xung đột, AI Rewrite và Quản lý Modal an toàn.
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("📚 Knowledge Dashboard JS initialized.");

    // Gắn sự kiện lắng nghe để dọn dẹp backdrop dư thừa nếu có xung đột DOM
    document.addEventListener('hidden.bs.modal', function (event) {
        if (!document.querySelector('.modal.show')) {
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
        }
    });
});

/**
 * Hàm helper chuẩn hóa lấy hoặc tạo Modal instance, chống lỗi backdrop của Bootstrap 5.
 */
function getOrCreateModal(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) {
        console.warn(`⚠️ Không tìm thấy phần tử modal với ID: ${modalId}`);
        return null;
    }
    // Sử dụng getOrCreateInstance chuẩn Bootstrap 5
    return bootstrap.Modal.getOrCreateInstance(modalEl);
}

/**
 * Lấy CSRF Token từ thẻ meta hoặc cookie để thực hiện các request an toàn.
 */
function getCsrfToken() {
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (metaToken) return metaToken;

    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 11) === ('csrftoken=')) {
                cookieValue = decodeURIComponent(cookie.substring(11));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Phê duyệt chương tri thức (P1 - Human-in-the-Loop).
 */
function approveChapter(chapterId) {
    if (!confirm("Bạn có chắc chắn muốn phê duyệt chương này? Dữ liệu sẽ được đồng bộ vào Vector Store.")) return;

    fetch(`/groups/api/knowledge/chapters/${chapterId}/approve/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert("Phê duyệt thành công!");
                location.reload();
            } else {
                alert("Lỗi: " + (data.message || 'Không thể phê duyệt.'));
            }
        })
        .catch(err => console.error('Error:', err));
}

/**
 * Giải quyết mâu thuẫn ngữ nghĩa (Semantic Overlap Resolution).
 */
function resolveConflict(chapterId) {
    const strategy = prompt("Chọn phương án: MERGE, OVERWRITE, IGNORE", "MERGE")?.toUpperCase();
    if (!strategy || !['MERGE', 'OVERWRITE', 'IGNORE'].includes(strategy)) return;

    fetch(`/groups/api/knowledge/chapters/${chapterId}/resolve-conflict/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ strategy })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert("Giải quyết thành công!");
                location.reload();
            } else {
                alert("Lỗi: " + (data.message || 'Xử lý thất bại.'));
            }
        })
        .catch(err => console.error('Error:', err));
}

/**
 * Gửi yêu cầu AI Rewrite và cập nhật giao diện bất đồng bộ.
 */
async function handleAIRewrite(chapterId, promptText, groupId) {
    try {
        const response = await fetch(`/api/group/${groupId}/knowledge/rewrite/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                chapter_id: chapterId,
                user_prompt: promptText,
                action_type: 'rewrite'
            })
        });

        if (!response.ok) throw new Error('Lỗi kết nối máy chủ.');

        const data = await response.json();

        const contentContainer = document.getElementById(`chapter-content-${chapterId}`);
        if (contentContainer) {
            contentContainer.innerHTML = data.content;
            console.log('Biên soạn thành công:', data.chapter_id);
        }
    } catch (error) {
        console.error('Lỗi AI Rewrite:', error);
        alert('Có lỗi xảy ra khi gọi AI.');
    }
}

/**
 * Thu thập dữ liệu từ Modal và gọi hàm handleAIRewrite bằng cơ chế an toàn.
 */
function submitAIRewrite() {
    const chapterId = document.getElementById('rewriteChapterId').value;
    const promptText = document.getElementById('aiPromptInput').value;

    const container = document.getElementById('knowledge-dashboard-container');
    const groupId = container ? container.dataset.groupId : null;

    if (!groupId) {
        alert("Không xác định được mã nhóm (group_id).");
        return;
    }

    if (promptText.length < 5) {
        alert("Vui lòng nhập yêu cầu biên soạn (tối thiểu 5 ký tự).");
        return;
    }

    // Đóng Modal an toàn sử dụng helper getOrCreateModal
    const modal = getOrCreateModal('aiRewriteModal');
    if (modal) {
        modal.hide();
    }

    // Gọi hàm xử lý bất đồng bộ
    handleAIRewrite(chapterId, promptText, groupId);
}