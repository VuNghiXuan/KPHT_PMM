document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("ai-model-form");
    if (!form) return;

    // 👁️ Toggle Password Visibility
    const toggleBtn = document.getElementById("toggle-password-btn");
    const apiKeyInput = document.getElementById("custom-api-key");
    const eyeIcon = document.getElementById("toggle-eye-icon");

    if (toggleBtn && apiKeyInput) {
        toggleBtn.addEventListener("click", function () {
            if (apiKeyInput.type === "password") {
                apiKeyInput.type = "text";
                if (eyeIcon) eyeIcon.classList.replace("fa-eye", "fa-eye-slash");
            } else {
                apiKeyInput.type = "password";
                if (eyeIcon) eyeIcon.classList.replace("fa-eye-slash", "fa-eye");
            }
        });
    }

    const customProviderSelect = document.getElementById('custom-ai-provider-select');
    const customModelInput = document.getElementById('custom-ai-model-input');
    const activeModelEl = document.getElementById('active-ai-model');
    const providerEl = document.getElementById('ai-provider');
    const presetSelect = document.getElementById("preset-ai-select");
    const testValidateBtn = document.getElementById("test-validate-ai-btn");

    // ⚡ Hàm hiển thị hoặc ẩn API Key dựa trên Provider
    function handleApiKeyVisibility(provider) {
        const apiKeyContainer = document.getElementById('api-key-container');
        if (apiKeyContainer) {
            apiKeyContainer.style.display = (provider === 'ollama') ? 'none' : 'block';
        }
    }

    // ⚡ Preset Selection Logic
    if (presetSelect) {
        presetSelect.addEventListener("change", function () {
            if (!this.value) return;
            const [provider, model] = this.value.split('|');

            if (providerEl) providerEl.value = provider;
            if (activeModelEl) activeModelEl.value = model;

            if (customProviderSelect) customProviderSelect.value = provider;
            if (customModelInput) customModelInput.value = model;

            handleApiKeyVisibility(provider);
        });
    }

    // ⚡ Custom Provider Synchronization
    if (customProviderSelect) {
        customProviderSelect.addEventListener("change", function () {
            const provider = this.value;
            if (providerEl) providerEl.value = provider;
            handleApiKeyVisibility(provider);
        });
    }

    // ⚡ Custom Model Synchronization
    if (customModelInput) {
        customModelInput.addEventListener("input", function () {
            if (activeModelEl) {
                activeModelEl.value = this.value;
            }
        });
    }

    // 🚀 Quy trình Kiểm tra tính hợp lệ (Validation) & Lưu cấu hình
    if (testValidateBtn) {
        testValidateBtn.addEventListener("click", async function (e) {
            e.preventDefault();

            const provider = customProviderSelect ? customProviderSelect.value : "gemini";
            const model = customModelInput ? customModelInput.value.trim() : "";
            const apiKey = apiKeyInput ? apiKeyInput.value.trim() : "";
            const validateUrl = form.getAttribute("data-validate-url");
            const saveUrl = form.getAttribute("data-url");

            if (!model) {
                alert("⚠️ Vui lòng nhập tên model cụ thể trước khi kiểm tra!");
                return;
            }

            // Cập nhật trạng thái nút bấm
            testValidateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Đang kết nối kiểm tra...';
            testValidateBtn.disabled = true;

            try {
                // Bước 1: Gửi request kiểm tra kết nối với Model / Provider thực tế
                let validateResponse = await fetch(validateUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": form.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        ai_provider: provider,
                        ai_model: model,
                        custom_api_key: apiKey
                    })
                });

                let validateData = await validateResponse.json();

                if (!validateResponse.ok || validateData.status !== 'success') {
                    alert("❌ Lỗi xác thực Model: " + (validateData.message || "Model không phản hồi hoặc không tồn tại."));
                    return;
                }

                // Bước 2: Nếu validate thành công, tiến hành lưu chính thức vào DB
                testValidateBtn.innerHTML = '<i class="fas fa-save fa-spin me-1"></i> Đang lưu cấu hình...';

                let saveResponse = await fetch(saveUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": form.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        ai_provider: provider,
                        ai_model: model,
                        custom_api_key: apiKey ? apiKey : null
                    })
                });

                let saveData = await saveResponse.json();

                if (saveResponse.ok && saveData.status === 'success') {
                    alert("✅ " + saveData.message);
                    location.reload();
                } else {
                    alert("❌ Lỗi lưu cấu hình: " + (saveData.message || "Không thể ghi nhận vào hệ thống."));
                }

            } catch (error) {
                console.error("Lỗi kết nối hệ thống:", error);
                alert("❌ Đã xảy ra lỗi mạng hoặc không thể kết nối tới máy chủ AI.");
            } finally {
                testValidateBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Kiểm tra tính hợp lệ & Lưu 💾';
                testValidateBtn.disabled = false;
            }
        });
    }
});