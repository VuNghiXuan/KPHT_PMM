document.addEventListener('DOMContentLoaded', function () {
    const detailModal = document.getElementById('knowledgeDetailModal');

    // Xử lý sự kiện click nút xem chi tiết
    document.querySelectorAll('.btn-inspect-knowledge').forEach(button => {
        button.addEventListener('click', function () {
            const id = this.dataset.id;
            const content = this.dataset.content;

            // Cập nhật thông tin vào Modal
            document.getElementById('modal-file-name').innerText = this.dataset.filename;
            document.getElementById('modal-entity-name').innerText = this.dataset.entity;
            document.getElementById('modal-content-preview').innerText = content;

            // Cập nhật link hành động (Duyệt/Từ chối)
            document.getElementById('modal-btn-approve').href = `/group/${groupId}/knowledge/${id}/approve/`;
            document.getElementById('modal-btn-reject').href = `/group/${groupId}/knowledge/${id}/reject/`;
        });
    });
});