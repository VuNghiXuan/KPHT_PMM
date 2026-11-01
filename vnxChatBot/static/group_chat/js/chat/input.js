/**
 * File: static/group_chat/js/chat/input.js
 * Mục đích: Quản lý khung nhập liệu, tích hợp @mention thông minh và upload file RAG theo chuẩn Group-Centric.
 * Tác giả: Kỹ sư hệ thống vnxChatBot
 */
class ChatInputManager {
    constructor(config) {
        console.log("[ChatInputManager] 🔄 Đang khởi tạo với cấu hình:", config);
        this.inputChat = document.getElementById(config.inputId);
        this.mentionDropdown = document.getElementById(config.dropdownId);
        this.fileInput = document.getElementById(config.fileInputId);
        this.filePreview = document.getElementById(config.previewId);
        this.groupMembers = config.members || [];

        if (!this.inputChat) console.error(`[ChatInputManager] ❌ Không tìm thấy ô input với ID: ${config.inputId}`);
        if (!this.mentionDropdown) console.error(`[ChatInputManager] ❌ Không tìm thấy dropdown với ID: ${config.dropdownId}`);
        if (!this.fileInput) console.warn(`[ChatInputManager] ⚠️ Không tìm thấy thẻ input file với ID: ${config.fileInputId}`);

        if (this.inputChat && this.mentionDropdown) {
            this.initEventListeners();
            console.log("[ChatInputManager] ✅ Khởi tạo thành công hệ thống Nhập liệu & Mention.");
        }
    }

    initEventListeners() {
        console.log("[ChatInputManager] 🔗 Đang thiết lập các bộ lắng nghe sự kiện (Event Listeners)...");

        this.inputChat.addEventListener("input", (e) => {
            this.handleChatInput(e);
        });

        if (this.fileInput) {
            this.fileInput.addEventListener("change", (e) => {
                console.log("[ChatInputManager] 📁 Phát hiện sự kiện chọn file. Số lượng file:", this.fileInput.files.length);
                this.handleFileUpload(e);
            });
        }

        document.addEventListener("click", (e) => {
            if (this.mentionDropdown.style.display === "block" &&
                !this.inputChat.contains(e.target) &&
                !this.mentionDropdown.contains(e.target)) {
                this.mentionDropdown.style.display = "none";
            }
        });
    }

    handleChatInput(e) {
        const cursorPosition = this.inputChat.selectionStart;
        const textBeforeCursor = this.inputChat.value.substring(0, cursorPosition);
        const words = textBeforeCursor.split(" ");
        const lastWord = words[words.length - 1];

        if (lastWord.startsWith("@")) {
            const query = lastWord.substring(1).toLowerCase();
            const filteredMembers = this.groupMembers.filter(m => m.username.toLowerCase().includes(query));

            if (filteredMembers.length > 0) {
                this.renderMentionDropdown(filteredMembers);
                this.mentionDropdown.style.display = "block";
            } else {
                this.mentionDropdown.style.display = "none";
            }
        } else {
            this.mentionDropdown.style.display = "none";
        }
    }

    renderMentionDropdown(members) {
        this.mentionDropdown.innerHTML = "";
        members.forEach(member => {
            const item = document.createElement("a");
            item.href = "#";
            item.className = "dropdown-item small py-1 px-2 rounded d-flex align-items-center gap-2";
            item.innerHTML = `<span>${member.display}</span>`;
            item.onclick = (e) => {
                e.preventDefault();
                this.insertMention(member.username);
            };
            this.mentionDropdown.appendChild(item);
        });
    }

    insertMention(username) {
        const cursorPosition = this.inputChat.selectionStart;
        const text = this.inputChat.value;
        const lastAtIndex = text.lastIndexOf("@", cursorPosition);

        if (lastAtIndex !== -1) {
            const newText = text.substring(0, lastAtIndex) + "@" + username + " " + text.substring(cursorPosition);
            this.inputChat.value = newText;
            this.inputChat.focus();
            const newCursorPos = lastAtIndex + username.length + 2;
            this.inputChat.setSelectionRange(newCursorPos, newCursorPos);
        }
        this.mentionDropdown.style.display = "none";
    }

    handleFileUpload(e) {
        const files = this.fileInput.files;
        if (files.length > 0) {
            let fileNames = Array.from(files).map(f => f.name);
            if (this.filePreview) {
                this.filePreview.textContent = `Đang tải lên: ${fileNames.join(", ")}...`;
            }
            this.uploadFilesToKnowledgeBase(files);
        }
    }

    uploadFilesToKnowledgeBase(files) {
        const uploadUrl = this.fileInput.getAttribute("data-upload-url");
        if (!uploadUrl) {
            console.error("[ChatInputManager] ❌ Lỗi: Thiếu thuộc tính data-upload-url!");
            if (this.filePreview) this.filePreview.textContent = "❌ Lỗi: Thiếu URL tải lên tài liệu!";
            return;
        }

        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append("file", file);
        });

        // 🎯 [Single Source of Truth]: Sử dụng hằng số chuẩn duy nhất theo template chat_detail.html
        const CHAT_CONTAINER_ID = 'message-list-container';
        const chatMessagesContainer = document.getElementById(CHAT_CONTAINER_ID);

        if (!chatMessagesContainer) {
            console.error(`[ChatInputManager] ❌ Lỗi kiến trúc: Không tìm thấy container chuẩn #${CHAT_CONTAINER_ID}`);
            if (this.filePreview) this.filePreview.textContent = "❌ Lỗi giao diện: Không tìm thấy khung chat!";
            return;
        }

        const groupId = window.currentGroupId || chatMessagesContainer.dataset.groupId;
        if (groupId) {
            formData.append("group_id", groupId);
        }

        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
            document.querySelector("meta[name=csrf-token]")?.content;

        fetch(uploadUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken || ""
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    // 📥 [Realtime UI Update]: Chèn ngay HTML tin nhắn file mới trả về vào khung chat chuẩn
                    if (data.html) {
                        chatMessagesContainer.insertAdjacentHTML('beforeend', data.html);
                        console.log("[ChatInputManager] 📥 Đã render trực tiếp tin nhắn tài liệu mới lên giao diện.");
                    }

                    // 📜 Tự động cuộn xuống đáy khung chat
                    if (window.chatCore && typeof window.chatCore.scrollToBottom === 'function') {
                        window.chatCore.scrollToBottom();
                    }

                    // 🧹 Reset input file sau khi upload thành công
                    this.fileInput.value = "";
                    if (this.filePreview) {
                        this.filePreview.textContent = "✅ Đã nạp tài liệu vào Kho Tri thức thành công!";
                        setTimeout(() => { this.filePreview.textContent = ""; }, 4000);
                    }
                } else {
                    if (this.filePreview) {
                        this.filePreview.textContent = `❌ Lỗi: ${data.message || 'Không xác định'}`;
                    }
                }
            })
            .catch(error => {
                console.error("[ChatInputManager] ❌ Lỗi kết nối:", error);
                if (this.filePreview) {
                    this.filePreview.textContent = "❌ Lỗi kết nối máy chủ!";
                }
            });
    }
}