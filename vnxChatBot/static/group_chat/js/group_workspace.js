/**
 * 📁 Path: static/group_chat/js/group_workspace.js
 * 📝 Mô tả: Quản lý ủy quyền sự kiện (Event Delegation) chung cho không gian làm việc nhóm.
 * Tuân thủ chuẩn Modular Monolith và Group-Centric.
 */

document.addEventListener('DOMContentLoaded', function () {
    const messageContainer = document.getElementById('message-list-container');

    if (!messageContainer) {
        console.warn("⚠️ Không tìm thấy phần tử #message-list-container trong DOM.");
        return;
    }

    // 🎯 Lắng nghe các sự kiện chung khác của workspace tại đây (nếu có)
    messageContainer.addEventListener('click', function (e) {
        // Lưu ý: Logic xử lý nút AI Learn đã được tách độc lập sang KnowledgeLearner 
        // để đảm bảo nguyên tắc phân tách trách nhiệm (Separation of Concerns).
    });
});