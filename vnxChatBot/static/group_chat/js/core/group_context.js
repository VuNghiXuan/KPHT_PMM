window.VNXContext = {
    group: {
        id: "{{ group.id }}", // Đảm bảo template render ra giá trị này
        name: "{{ group.name }}"
    },
    user: {
        username: "{{ request.user.username }}",
        avatar: "{% if request.user.profile.avatar %}{{ request.user.profile.avatar.url }}{% endif %}"
    },
    aiConfig: {
        model: localStorage.getItem('ai_model') || 'gemini-1.5-pro',
        temperature: localStorage.getItem('ai_temp') || 0.7
    },
    // Cơ chế cập nhật cấu hình động
    updateAIConfig(newConfig) {
        this.aiConfig = { ...this.aiConfig, ...newConfig };
        console.log("🔄 AI Config updated:", this.aiConfig);
        window.dispatchEvent(new CustomEvent('aiConfigChanged', { detail: this.aiConfig }));
    }
};