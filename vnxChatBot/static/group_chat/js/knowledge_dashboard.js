/**
 * File: static/group_chat/js/knowledge_dashboard.js
 * Mô tả: Xử lý tương tác Master-Detail, duyệt hàng loạt (Batch Operations) và AI Power.
 */

// Biến lưu trữ trạng thái dữ liệu trên Client
let activeChapterData = null;

document.addEventListener("DOMContentLoaded", function () {
    console.log("📚 Knowledge Dashboard JS (Master-Detail) đã khởi tạo.");

    // 1. Lắng nghe các sự kiện chính
    initBatchToolbar();
    initFilterHandler();
    updateChapterCounts();

    // 2. Tự động chọn chương đầu tiên trong danh sách (nếu có)
    const firstCard = document.querySelector('.chapter-item-card');
    if (firstCard) {
        const firstId = firstCard.dataset.chapterId;
        selectChapter(firstId);
    }

    // 3. Dọn dẹp backdrop dư thừa khi modal đóng
    document.addEventListener('hidden.bs.modal', function () {
        if (!document.querySelector('.modal.show')) {
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
        }
    });

    // 4. Đăng ký sự kiện nút bấm trong Modal & UI
    const saveBtn = document.getElementById('saveChapterChangesBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveChapterEdit);
    }

    const aiSubmitBtn = document.getElementById('submitAIRewriteBtn');
    if (aiSubmitBtn) {
        aiSubmitBtn.addEventListener('click', submitAIRewrite);
    }

    const editBtn = document.getElementById('editChapterBtn');
    if (editBtn) {
        editBtn.addEventListener('click', openEditModal);
    }

    const aiModalBtn = document.getElementById('openAIRewriteBtn');
    if (aiModalBtn) {
        aiModalBtn.addEventListener('click', openAIRewriteModal);
    }
});

/* ==========================================================================
   HELPER FUNCTIONS (CÁC HÀM BỔ TRỢ)
   ========================================================================== */

function getOrCreateModal(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return null;
    return bootstrap.Modal.getOrCreateInstance(modalEl);
}

function getCsrfToken() {
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (metaToken) return metaToken;

    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                cookieValue = decodeURIComponent(cookie.substring(11));
                break;
            }
        }
    }
    return cookieValue;
}

function getGroupId() {
    const container = document.getElementById('knowledge-dashboard-container');
    return container ? container.dataset.groupId : null;
}

/* ==========================================================================
   MASTER-DETAIL VIEW LOGIC (XỬ LÝ CHỌN VÀ HIỂN THỊ CHI TIẾT)
   ========================================================================== */

function selectChapter(chapterId) {
    // 1. Đổi class active giữa các Card bên danh sách
    const cards = document.querySelectorAll('.chapter-item-card');
    cards.forEach(card => card.classList.remove('active'));

    const selectedCard = document.querySelector(`.chapter-item-card[data-chapter-id="${chapterId}"]`);
    if (!selectedCard) return;

    selectedCard.classList.add('active');

    // 2. Lấy dữ liệu từ thẻ JSON nhúng sẵn trong HTML
    const dataScript = document.getElementById(`chapter-data-${chapterId}`);
    if (!dataScript) {
        console.error(`Không tìm thấy thẻ JSON dữ liệu cho chapter ID: ${chapterId}`);
        return;
    }

    let chapterData;
    try {
        chapterData = JSON.parse(dataScript.textContent);
    } catch (e) {
        console.error('Lỗi phân tích cú pháp JSON:', e);
        return;
    }

    // 3. Lưu dữ liệu đang chọn vào biến toàn cục activeChapterData
    activeChapterData = {
        id: chapterData.id,
        title: chapterData.title,
        summary: chapterData.summary,
        content: chapterData.content,
        status: chapterData.status,
        hasConflict: chapterData.has_conflict,
        conflictReason: chapterData.conflict_reason
    };

    // 4. Hiển thị Detail Pane & cập nhật thông tin
    const emptyState = document.getElementById('detailEmptyState');
    const contentPane = document.getElementById('detailContentPane');
    if (emptyState) emptyState.classList.add('d-none');
    if (contentPane) contentPane.classList.remove('d-none');

    const titleEl = document.getElementById('detailTitle');
    const summaryEl = document.getElementById('detailSummary');
    const bodyContentEl = document.getElementById('detailBodyContent');
    const updatedAtEl = document.getElementById('detailUpdatedAt');

    if (titleEl) titleEl.innerText = chapterData.title || 'Không có tiêu đề';
    if (summaryEl) summaryEl.innerText = chapterData.summary || 'Không có tóm tắt';
    if (updatedAtEl) updatedAtEl.innerText = chapterData.updated_at || '';

    // 💡 Hiển thị nội dung trực tiếp (Đã loại bỏ việc gọi API phụ)
    if (bodyContentEl) {
        bodyContentEl.innerText = (chapterData.content && chapterData.content.trim() !== '')
            ? chapterData.content
            : (chapterData.summary || 'Chưa có nội dung chi tiết.');
    }

    // Cập nhật Badge Trạng thái
    const badge = document.getElementById('detailStatusBadge');
    if (badge) {
        badge.innerText = (chapterData.status || 'pending').toUpperCase();
        badge.className = 'badge mb-2 ' + (
            chapterData.status === 'approved' ? 'bg-success' :
                chapterData.status === 'conflict_detected' ? 'bg-danger' : 'bg-warning text-dark'
        );
    }

    // Cảnh báo mâu thuẫn
    const conflictBanner = document.getElementById('detailConflictBanner');
    const conflictReasonElem = document.getElementById('detailConflictReason');

    if (conflictBanner) {
        if (chapterData.has_conflict || chapterData.status === 'conflict_detected') {
            conflictBanner.style.display = 'block';
            if (conflictReasonElem) {
                conflictReasonElem.innerText = chapterData.conflict_reason || 'Chương này có nội dung mâu thuẫn với dữ liệu hiện có.';
            }
        } else {
            conflictBanner.style.display = 'none';
        }
    }

    // 5. Gán sự kiện cho nút Phê duyệt / Từ chối đơn lẻ
    const singleApproveBtn = document.getElementById('singleApproveBtn');
    const singleRejectBtn = document.getElementById('singleRejectBtn');

    if (singleApproveBtn) {
        singleApproveBtn.onclick = () => approveChapter(getGroupId(), chapterId);
    }
    if (singleRejectBtn) {
        singleRejectBtn.onclick = () => rejectChapter(getGroupId(), chapterId);
    }
}

function loadChapterBodyContent(chapterId) {
    const bodyContentEl = document.getElementById('detailBodyContent');
    if (!bodyContentEl) return;

    bodyContentEl.innerHTML = '<span class="text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Đang tải nội dung...</span>';

    const groupId = getGroupId();
    fetch(`/groups/${groupId}/knowledge/chapters/${chapterId}/detail-api/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' || data.content) {
                const content = data.content || data.body || 'Không có nội dung chi tiết.';
                bodyContentEl.innerText = content;
                if (activeChapterData) activeChapterData.content = content;
            } else {
                bodyContentEl.innerText = 'Không thể tải nội dung chi tiết.';
            }
        })
        .catch(() => {
            bodyContentEl.innerText = activeChapterData?.summary || 'Nội dung chưa được tải.';
        });
}

/* ==========================================================================
   BATCH OPERATIONS LOGIC (THAO TÁC HÀNG LOẠT)
   ========================================================================== */

function initBatchToolbar() {
    const selectAllCb = document.getElementById('selectAllChapters');
    const bulkApproveBtn = document.getElementById('bulkApproveBtn');
    const bulkRejectBtn = document.getElementById('bulkRejectBtn');

    if (selectAllCb) {
        selectAllCb.addEventListener('change', function () {
            const visibleCheckboxes = document.querySelectorAll('.chapter-item-card:not([style*="display: none"]) .chapter-select-checkbox');
            visibleCheckboxes.forEach(cb => cb.checked = selectAllCb.checked);
            updateSelectedCount();
        });
    }

    document.getElementById('masterChapterList')?.addEventListener('change', function (e) {
        if (e.target.classList.contains('chapter-select-checkbox')) {
            updateSelectedCount();
        }
    });

    if (bulkApproveBtn) {
        bulkApproveBtn.addEventListener('click', function () {
            const selectedIds = getSelectedChapterIds();
            if (selectedIds.length === 0) return;
            if (confirm(`Bạn có chắc muốn phê duyệt ${selectedIds.length} chương đã chọn?`)) {
                executeBatchAction('approve', selectedIds);
            }
        });
    }

    if (bulkRejectBtn) {
        bulkRejectBtn.addEventListener('click', function () {
            const selectedIds = getSelectedChapterIds();
            if (selectedIds.length === 0) return;
            if (confirm(`Bạn có chắc muốn từ chối ${selectedIds.length} chương đã chọn?`)) {
                executeBatchAction('reject', selectedIds);
            }
        });
    }
}

function getSelectedChapterIds() {
    const checkboxes = document.querySelectorAll('.chapter-select-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function updateSelectedCount() {
    const selectedCount = getSelectedChapterIds().length;
    const countSpan = document.getElementById('selectedCount');
    const bulkActionBtns = document.getElementById('bulkActionButtons');

    if (countSpan) countSpan.innerText = selectedCount;
    if (bulkActionBtns) {
        bulkActionBtns.style.display = selectedCount > 0 ? 'inline-flex' : 'none';
    }
}

function updateChapterCounts() {
    const totalCards = document.querySelectorAll('.chapter-item-card').length;
    const totalSpan = document.getElementById('totalChapterCount');
    const badgeSpan = document.getElementById('chapterListBadge');

    if (totalSpan) totalSpan.innerText = totalCards;
    if (badgeSpan) badgeSpan.innerText = totalCards;
}

function executeBatchAction(actionType, chapterIds) {
    const groupId = getGroupId();
    fetch(`/groups/${groupId}/knowledge/batch-action/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: actionType,
            chapter_ids: chapterIds
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert(`Đã thực hiện [${actionType.toUpperCase()}] thành công cho ${chapterIds.length} mục!`);
                location.reload();
            } else {
                alert('Lỗi: ' + (data.message || 'Không thể xử lý hàng loạt.'));
            }
        })
        .catch(err => {
            console.error('Lỗi Batch Action:', err);
            alert('Đã xảy ra lỗi trong quá trình xử lý hàng loạt.');
        });
}

/* ==========================================================================
   FILTER LOGIC (BỘ LỌC TRẠNG THÁI)
   ========================================================================== */

function initFilterHandler() {
    const filterSelect = document.getElementById('statusFilterSelect');
    if (!filterSelect) return;

    filterSelect.addEventListener('change', function () {
        const filterValue = this.value;
        const cards = document.querySelectorAll('.chapter-item-card');

        cards.forEach(card => {
            const status = card.dataset.status;
            if (filterValue === 'all' || status === filterValue) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });

        const selectAllCb = document.getElementById('selectAllChapters');
        if (selectAllCb) selectAllCb.checked = false;
        document.querySelectorAll('.chapter-select-checkbox').forEach(cb => cb.checked = false);
        updateSelectedCount();
    });
}

/* ==========================================================================
   SINGLE CHAPTER ACTIONS & EDIT MODAL
   ========================================================================== */

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

function rejectChapter(groupId, chapterId) {
    if (!confirm("Bạn có chắc chắn muốn từ chối chương này?")) return;

    fetch(`/groups/${groupId}/knowledge/chapters/${chapterId}/reject-api/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert("Đã từ chối chương.");
                location.reload();
            } else {
                alert("Lỗi: " + (data.message || 'Không thể xử lý.'));
            }
        })
        .catch(err => console.error('Error:', err));
}

function openEditModal() {
    if (!activeChapterData) return;

    const idInput = document.getElementById('activeChapterId');
    const titleInput = document.getElementById('detailChapterTitle');
    const summaryInput = document.getElementById('detailChapterSummary');
    const contentInput = document.getElementById('detailChapterContent');

    if (idInput) idInput.value = activeChapterData.id;
    if (titleInput) titleInput.value = activeChapterData.title || '';
    if (summaryInput) summaryInput.value = activeChapterData.summary || '';
    if (contentInput) {
        contentInput.value = activeChapterData.content || document.getElementById('detailBodyContent')?.innerText || '';
    }

    const modal = getOrCreateModal('knowledgeDetailModal');
    if (modal) modal.show();
}

function saveChapterEdit() {
    const chapterId = document.getElementById('activeChapterId')?.value;
    const title = document.getElementById('detailChapterTitle')?.value;
    const summary = document.getElementById('detailChapterSummary')?.value;
    const content = document.getElementById('detailChapterContent')?.value;
    const groupId = getGroupId();

    if (!chapterId || !groupId) return;

    fetch(`/groups/${groupId}/knowledge/chapters/${chapterId}/update/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ title, summary, content })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert("Lưu thay đổi thành công!");
                const modal = getOrCreateModal('knowledgeDetailModal');
                if (modal) modal.hide();
                location.reload();
            } else {
                alert("Lỗi: " + (data.message || 'Không thể lưu thay đổi.'));
            }
        })
        .catch(err => console.error('Lỗi lưu chương:', err));
}

/* ==========================================================================
   AI REWRITE LOGIC
   ========================================================================== */

function openAIRewriteModal() {
    if (!activeChapterData) {
        alert("Vui lòng chọn một chương trước.");
        return;
    }

    const chapterIdInput = document.getElementById('rewriteChapterId');
    const promptInput = document.getElementById('aiPromptInput');

    if (chapterIdInput) chapterIdInput.value = activeChapterData.id;
    if (promptInput) promptInput.value = '';

    const modal = getOrCreateModal('aiRewriteModal');
    if (modal) modal.show();
}

function submitAIRewrite() {
    const chapterId = document.getElementById('rewriteChapterId')?.value;
    const promptText = document.getElementById('aiPromptInput')?.value;
    const groupId = getGroupId();

    if (!groupId || !chapterId) {
        alert("Không xác định được mã nhóm hoặc mã chương.");
        return;
    }

    if (!promptText || promptText.trim().length < 5) {
        alert("Vui lòng nhập yêu cầu biên soạn (tối thiểu 5 ký tự).");
        return;
    }

    const modal = getOrCreateModal('aiRewriteModal');
    if (modal) modal.hide();

    handleAIRewrite(chapterId, promptText, groupId);
}

async function handleAIRewrite(chapterId, promptText, groupId) {
    const bodyContentEl = document.getElementById('detailBodyContent');
    if (bodyContentEl) {
        bodyContentEl.innerHTML = '<div class="text-center py-3 text-warning"><i class="fas fa-robot fa-spin me-2"></i>AI đang thực hiện biên soạn lại nội dung...</div>';
    }

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

        if (data.status === 'success' || data.content) {
            const newContent = data.content || data.body;
            if (bodyContentEl) bodyContentEl.innerText = newContent;
            if (activeChapterData) activeChapterData.content = newContent;
            alert("Biên soạn lại nội dung bằng AI thành công!");
        } else {
            alert("Lỗi AI: " + (data.message || 'Không thể biên soạn lại.'));
            selectChapter(chapterId);
        }
    } catch (error) {
        console.error('Lỗi AI Rewrite:', error);
        alert('Có lỗi xảy ra khi gọi AI.');
        selectChapter(chapterId);
    }
}