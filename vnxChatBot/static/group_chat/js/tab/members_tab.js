/**
 * File: apps/group_chat/static/group_chat/js/tab/members_tab.js
 * Mục đích: Xử lý logic sự kiện form thêm thành viên nhóm qua AJAX.
 */

document.addEventListener('DOMContentLoaded', function () {
    const addMemberForm = document.getElementById('add-member-form');
    if (!addMemberForm) return;

    const groupId = addMemberForm.getAttribute('data-group-id');

    addMemberForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const identifierInput = document.getElementById('new-member-username');
        const roleSelect = document.getElementById('new-member-role');

        const identifier = identifierInput.value.trim();
        const role = roleSelect.value;

        if (!identifier) {
            alert('⚠️ Vui lòng nhập thông tin username hoặc email!');
            return;
        }

        addMemberToGroup(groupId, identifier, role);
    });
});

function addMemberToGroup(groupId, identifier, role = 'member') {
    const url = `/groups/${groupId}/add-member/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ username: identifier, role: role })
    })
        .then(async response => {
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error(`Server trả về mã lỗi HTTP ${response.status}`);
            }
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Lỗi hệ thống.');
            return data;
        })
        .then(data => {
            if (data.status === 'success') {
                alert("✅ " + data.message);
                location.reload();
            } else {
                alert("⚠️ " + data.message);
            }
        })
        .catch(error => {
            alert('❌ Thêm thành viên thất bại: ' + error.message);
        });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}