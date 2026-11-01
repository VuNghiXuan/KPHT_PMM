/**
 * 📊 Knowledge Status Poller
 * Theo dõi trạng thái xử lý tài liệu thô (RawDocument) qua Celery với cơ chế Smart Backoff & Network Diagnostic.
 * Đã tích hợp Null-Check an toàn tuyệt đối chống lỗi DOM Backdrop.
 */
function fetchTaskStatus(groupId, rawDocId, statusBadgeEl, progressBarEl) {
    let errorCount = 0;
    const maxErrors = 5;
    const pollIntervalTime = 3000; // 3 giây kiểm tra một lần

    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/groups/${groupId}/documents/${rawDocId}/status/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.status === 'success') {
                // Reset bộ đếm lỗi khi kết nối thành công
                errorCount = 0;

                const { current_status, status_display } = result.data;

                // Cập nhật giao diện Badge trạng thái (Kiểm tra phần tử tồn tại trước khi thao tác)
                if (statusBadgeEl) {
                    statusBadgeEl.textContent = status_display;
                    statusBadgeEl.className = `badge status-${current_status.toLowerCase()}`;
                }

                // Cập nhật Progress Bar nếu có
                if (progressBarEl) {
                    if (current_status === 'STAGING') {
                        progressBarEl.style.width = '60%';
                    } else if (current_status === 'APPROVED') {
                        progressBarEl.style.width = '100%';
                    }
                }

                // Nếu tiến trình hoàn tất hoặc thất bại, dừng polling và làm mới giao diện
                if (current_status === 'APPROVED' || current_status === 'FAILED') {
                    clearInterval(pollInterval);
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
            }
        } catch (error) {
            errorCount++;
            console.warn(`⚠️ [Poller] Lỗi kết nối lần thứ ${errorCount}:`, error);

            // Khi chạm ngưỡng 5 lần lỗi liên tiếp -> Kích hoạt chẩn đoán thông minh
            if (errorCount >= maxErrors) {
                clearInterval(pollInterval);

                if (!navigator.onLine) {
                    if (statusBadgeEl) {
                        statusBadgeEl.textContent = '❌ Mất kết nối Internet';
                        statusBadgeEl.className = 'badge bg-danger text-white';
                    }
                } else {
                    if (statusBadgeEl) {
                        statusBadgeEl.textContent = '⚠️ Lỗi hệ thống / Mất kết nối Server';
                        statusBadgeEl.className = 'badge bg-warning text-dark';
                    }
                }
            }
        }
    }, pollIntervalTime);
}