/**
 * File: static/group_chat/js/main.js
 * Mục đích: Nhạc trưởng trung tâm khởi chạy các module chức năng độc lập (WebSocket/ChatCore, 
 *           Reply, Reactions, Uploader, KnowledgeLearner) theo kiến trúc Modular Monolith.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 * Module liên kết: websocket.js, reply.js, reactions.js, uploader.js, knowledge_learner.js
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("[vnxChatBot] 🚀 Khởi động hệ thống Workspace nhóm chat...");

    // 1. Khởi tạo bộ xử lý lõi chat & WebSocket (Group-Centric isolation)
    if (typeof ChatWebSocketClient !== "undefined") {
        window.chatCore = new ChatWebSocketClient();

        // 🔗 Đồng bộ alias tham chiếu nhanh để tương thích ngược với các module gọi window.chatWs
        window.chatWs = window.chatCore;
        console.log("[Main] ✅ ChatWebSocketClient đã được kích hoạt và đồng bộ alias thành công.");
    } else {
        console.error("[Main] ❌ Không tìm thấy lớp ChatWebSocketClient. Hãy kiểm tra thứ tự nhúng file script!");
    }

    // 🚀 Tự động cuộn đến tin nhắn cuối ngay sau khi ChatCore/WebSocket đã khởi tạo và DOM sẵn sàng
    if (window.chatCore && typeof window.chatCore.scrollToBottom === 'function') {
        window.chatCore.scrollToBottom();
        console.log("[Main] 📜 Đã kích hoạt lệnh cuộn tự động xuống đáy khung chat.");
    }

    // 2. Khởi tạo module Trả lời trích dẫn (Reply)
    if (typeof ChatReplyManager !== "undefined") {
        window.chatReplyManager = new ChatReplyManager();
        console.log("[Main] ✅ ChatReplyManager đã được kích hoạt.");
    }

    // 3. Khởi tạo module Cảm xúc & Tương tác (Reactions)
    if (typeof ChatReactions !== "undefined") {
        window.chatReactions = new ChatReactions();
        console.log("[Main] ✅ ChatReactions đã được kích hoạt.");
    }

    // 4. Khởi tạo module Tải lên tài liệu (Document Uploader theo group_id)
    const groupId = window.currentGroupId || document.getElementById('chat-messages')?.dataset.groupId;
    if (typeof DocumentUploader !== "undefined" && groupId) {
        window.documentUploader = new DocumentUploader(groupId, 'chat-messages');
        console.log(`[Main] ✅ DocumentUploader đã được kích hoạt cho nhóm ID: ${groupId}`);
    }

    // 5. Khởi tạo module Quản lý Nhập liệu & @Mention (ChatInputManager)
    if (typeof ChatInputManager !== "undefined") {
        const groupMembers = window.groupMembersData || [
            { username: "AI Assistant", is_ai: true, display: "🤖 AI Assistant" },
            { username: "admin", is_ai: false, display: "👤 admin (Quản trị viên)" },
            { username: "abc", is_ai: false, display: "👤 abc (Thành viên)" }
        ];

        window.chatInputManager = new ChatInputManager({
            inputId: "chat-message-input",
            dropdownId: "mention-dropdown",
            fileInputId: "file-upload",
            previewId: "selected-files-preview",
            members: groupMembers
        });
        console.log("[Main] ✅ ChatInputManager đã được kích hoạt thành công.");
    }

    // 6. Khởi tạo context user toàn cục từ DOM
    const container = document.getElementById('message-list-container');
    if (container && container.dataset.userId) {
        window.currentUserId = parseInt(container.dataset.userId);
        console.log("[Main] 👤 Context User ID đã được thiết lập:", window.currentUserId);
    }

    // 7. Khởi tạo module Kích hoạt tiến trình học tập tài liệu (KnowledgeLearner)
    if (typeof KnowledgeLearner !== "undefined") {
        window.knowledgeLearner = new KnowledgeLearner();
        console.log("[Main] ✅ KnowledgeLearner đã được kích hoạt và sẵn sàng lắng nghe sự kiện học tri thức.");
    } else {
        console.warn("[Main] ⚠️ Không tìm thấy lớp KnowledgeLearner. Hãy kiểm tra thứ tự nhúng file script!");
    }

    console.log("[vnxChatBot] 🎉 Hoàn tất khởi chạy toàn bộ module!");
});