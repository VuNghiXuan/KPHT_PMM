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
            console.log("[ChatInputManager] ⌨️ Phát hiện sự kiện gõ phím tại ô input. Giá trị hiện tại:", this.inputChat.value);
            this.handleChatInput(e);
        });

        if (this.fileInput) {
            this.fileInput.addEventListener("change", (e) => {
                console.log("[ChatInputManager] 📁 Phát hiện sự kiện chọn file/folder. Số lượng file:", this.fileInput.files.length);
                this.handleFileUpload(e);
            });
        }

        document.addEventListener("click", (e) => {
            if (this.mentionDropdown.style.display === "block" &&
                !this.inputChat.contains(e.target) &&
                !this.mentionDropdown.contains(e.target)) {
                console.log("[ChatInputManager] 🖱️ Click ra ngoài vùng mention -> Ẩn dropdown.");
                this.mentionDropdown.style.display = "none";
            }
        });
    }

    handleChatInput(e) {
        const cursorPosition = this.inputChat.selectionStart;
        const textBeforeCursor = this.inputChat.value.substring(0, cursorPosition);
        const words = textBeforeCursor.split(" ");
        const lastWord = words[words.length - 1];

        console.log("[ChatInputManager] 🔍 Đang phân tích từ khóa tại con trỏ:", { cursorPosition, lastWord, groupMembersCount: this.groupMembers.length });

        if (lastWord.startsWith("@")) {
            const query = lastWord.substring(1).toLowerCase();
            const filteredMembers = this.groupMembers.filter(m => m.username.toLowerCase().includes(query));

            console.log(`[ChatInputManager] 🎯 Từ khóa tìm kiếm '@${query}': Tìm thấy ${filteredMembers.length} thành viên khớp.`);

            if (filteredMembers.length > 0) {
                this.renderMentionDropdown(filteredMembers);
                this.mentionDropdown.style.display = "block";
                console.log("[ChatInputManager] 📂 Đã hiển thị dropdown mention.");
            } else {
                this.mentionDropdown.style.display = "none";
                console.log("[ChatInputManager] 📂 Không có thành viên khớp -> Ẩn dropdown mention.");
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
                console.log(`[ChatInputManager] 👉 Người dùng chọn mention: ${member.username}`);
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
            console.log("[ChatInputManager] ✨ Đã chèn mention thành công:", newText);
        }
        this.mentionDropdown.style.display = "none";
    }

    handleFileUpload(e) {
        const files = this.fileInput.files;
        if (files.length > 0) {
            let fileNames = Array.from(files).map(f => f.name);
            if (this.filePreview) {
                this.filePreview.textContent = `Đã chọn: ${fileNames.join(", ")}`;
            }
            console.log("[ChatInputManager] 📤 Chuẩn bị tải lên các file:", fileNames);
            this.uploadFilesToKnowledgeBase(files);
        }
    }

    uploadFilesToKnowledgeBase(files) {
        const uploadUrl = this.fileInput.getAttribute("data-upload-url");
        console.log("[ChatInputManager] 🌐 Đường dẫn URL tải lên RAG:", uploadUrl);

        if (!uploadUrl) {
            console.error("[ChatInputManager] ❌ Lỗi: Thiếu thuộc tính data-upload-url trên input file!");
            if (this.filePreview) this.filePreview.textContent = "❌ Lỗi: Thiếu URL tải lên tài liệu!";
            return;
        }

        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append("documents", file);
            console.log(`[ChatInputManager] 📦 Thêm file vào FormData: ${file.name} (${file.size} bytes)`);
        });

        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
            document.querySelector("meta[name=csrf-token]")?.content;

        fetch(uploadUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken || ""
            }
        })
            .then(response => {
                console.log("[ChatInputManager] 📥 Nhận phản hồi từ Server, mã trạng thái:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("[ChatInputManager] 📄 Dữ liệu JSON trả về từ Server:", data);
                if (data.status === "success") {
                    if (this.filePreview) {
                        this.filePreview.textContent = "✅ Đã nạp tài liệu vào Kho Tri thức nhóm thành công!";
                        setTimeout(() => { this.filePreview.textContent = ""; }, 4000);
                    }
                } else {
                    if (this.filePreview) {
                        this.filePreview.textContent = `❌ Lỗi từ server: ${data.message || 'Không xác định'}`;
                    }
                }
            })
            .catch(error => {
                console.error("[ChatInputManager] ❌ Lỗi kết nối mạng hoặc xử lý AJAX:", error);
                if (this.filePreview) {
                    this.filePreview.textContent = "❌ Lỗi kết nối máy chủ!";
                }
            });
    }
}