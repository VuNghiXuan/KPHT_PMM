/**
 * File: static/group_chat/js/knowledge_dashboard.js
 * Mô tả: Xử lý tương tác Human-in-the-Loop và AI Power cho trang Knowledge Dashboard.
 * Đồng bộ hóa với endpoint giải quyết xung đột và quản lý Modal AI Rewrite chuẩn xác.
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("📚 Knowledge Dashboard JS initialized.");

    // Dọn dẹp backdrop dư thừa khi modal đóng để tránh lỗi khóa giao diện
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
 * Hàm helper: Lấy hoặc tạo Modal instance an toàn với Bootstrap 5.
 */
function getOrCreateModal(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) {
        console.warn(`⚠️ Không tìm thấy phần tử modal với ID: ${modalId}`);
        return null;
    }
    return bootstrap.Modal.getOrCreateInstance(modalEl);
}

/**
 * Lấy CSRF Token từ thẻ meta hoặc cookie để thực hiện request an toàn.
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
 * Phê duyệt chương tri thức (Human-in-the-Loop - P1).
 */
function approveChapter(groupId, chapterId) {
    if (!confirm("Bạn có chắc chắn muốn phê duyệt chương này? Dữ liệu sẽ được đồng bộ vào Vector Store.")) return;

    fetch(`/groups/${groupId}/knowledge/chapters/${chapterId}/approval-api/`, {
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
 * Giải quyết mâu thuẫn ngữ nghĩa (Conflict Resolution) chuẩn hóa theo URL patterns.
 */
function resolveChapterConflict(groupId, chapterId, actionType) {
    if (!confirm(`Bạn có chắc chắn muốn thực hiện hành động [${actionType.toUpperCase()}] đối với chương này không?`)) {
        return;
    }

    const resolveUrl = `/groups/${groupId}/knowledge/chapters/${chapterId}/resolve/`;

    fetch(resolveUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ action: actionType })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Đã xử lý xung đột tri thức thành công!');
                const row = document.getElementById(`chapter-row-${chapterId}`);
                if (row) {
                    row.style.transition = 'opacity 0.5s ease';
                    row.style.opacity = '0';
                    setTimeout(() => row.remove(), 500);
                } else {
                    location.reload();
                }
            } else {
                alert('Lỗi xử lý: ' + (data.detail || data.message || 'Không xác định'));
            }
        })
        .catch(error => {
            console.error('Lỗi kết nối:', error);
            alert('Đã xảy ra lỗi kết nối đến máy chủ.');
        });
}

/**
 * Mở giao diện Modal AI Rewrite và nạp sẵn ID chương cần biên soạn.
 */
function openAIRewriteModal(chapterId, currentSuggestion = '') {
    const chapterInput = document.getElementById('rewriteChapterId');
    if (chapterInput) {
        chapterInput.value = chapterId;
    }

    const promptInput = document.getElementById('aiPromptInput');
    if (promptInput) {
        promptInput.value = currentSuggestion || '';
    }

    const modal = getOrCreateModal('aiRewriteModal');
    if (modal) {
        modal.show();
    }
}

/**
 * Gửi yêu cầu AI Rewrite và cập nhật giao diện bất đồng bộ.
 */
async function handleAIRewrite(chapterId, promptText, groupId) {
    try {
        const response = await fetch(`/groups/${groupId}/knowledge/chapters/${chapterId}/rewrite/`, {
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
            alert("Biên soạn lại nội dung bằng AI thành công!");
        } else {
            alert("Biên soạn AI thành công!");
            location.reload();
        }
    } catch (error) {
        console.error('Lỗi AI Rewrite:', error);
        alert('Có lỗi xảy ra khi gọi AI.');
    }
}

/**
 * Thu thập dữ liệu từ Modal và gọi hàm handleAIRewrite an toàn.
 */
function submitAIRewrite() {
    const chapterId = document.getElementById('rewriteChapterId')?.value;
    const promptText = document.getElementById('aiPromptInput')?.value;

    const container = document.getElementById('knowledge-dashboard-container');
    const groupId = container ? container.dataset.groupId : null;

    if (!groupId || !chapterId) {
        alert("Không xác định được mã nhóm hoặc mã chương.");
        return;
    }

    if (!promptText || promptText.length < 5) {
        alert("Vui lòng nhập yêu cầu biên soạn (tối thiểu 5 ký tự).");
        return;
    }

    const modal = getOrCreateModal('aiRewriteModal');
    if (modal) {
        modal.hide();
    }

    handleAIRewrite(chapterId, promptText, groupId);
}


