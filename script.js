const API_URL = 'http://127.0.0.1:8000';

// 全域變數存放從後端取得的清單
let articles = [];

// 頁面載入時初始化
window.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    switchRole('author');
    fetchSubmissions();
});

// 1. 從後端取得所有稿件
async function fetchSubmissions() {
    try {
        const response = await fetch(`${API_URL}/api/submissions`);
        if (!response.ok) throw new Error('無法取得稿件資料');
        articles = await response.json();
        
        // 重新渲染目前所在的視角
        if (currentRole === 'author') {
            renderAuthorList();
        } else {
            renderEditorList();
        }
    } catch (error) {
        console.error("連線錯誤：", error);
        showToast("無法連線至後端伺服器");
    }
}

// Role Switcher
let currentRole = 'author';
function switchRole(role) {
    currentRole = role;
    const authorView = document.getElementById('view-author');
    const editorView = document.getElementById('view-editor');
    const btnAuthor = document.getElementById('role-btn-author');
    const btnEditor = document.getElementById('role-btn-editor');

    if (role === 'author') {
        authorView.classList.remove('hidden');
        editorView.classList.add('hidden');
        btnAuthor.className = "px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 bg-white text-stone-800 shadow-xs border border-stone-200/60";
        btnEditor.className = "px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 text-stone-500 hover:text-stone-800";
        renderAuthorList();
    } else {
        editorView.classList.remove('hidden');
        authorView.classList.add('hidden');
        btnEditor.className = "px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 bg-white text-stone-800 shadow-xs border border-stone-200/60";
        btnAuthor.className = "px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 text-stone-500 hover:text-stone-800";
        renderEditorList();
    }
    lucide.createIcons();
}

// Render Author List
function renderAuthorList() {
    const statusFilter = document.getElementById('author-status-filter').value;
    const categoryFilter = document.getElementById('author-category-filter').value;
    const tbody = document.getElementById('author-table-body');
    const emptyEl = document.getElementById('author-empty');
    const countBadge = document.getElementById('author-count-badge');

    let filtered = articles.filter(art => {
        const matchStatus = (statusFilter === 'all' || art.status === statusFilter);
        const matchCat = (categoryFilter === 'all' || art.category === categoryFilter);
        return matchStatus && matchCat;
    });

    countBadge.innerText = `共 ${filtered.length} 筆稿件`;

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        emptyEl.classList.remove('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    tbody.innerHTML = filtered.map(art => {
        let badgeClass = '';
        if (art.status === '編輯中') badgeClass = 'bg-amber-50 text-amber-800 border-amber-200/60';
        else if (art.status === '審查中') badgeClass = 'bg-sky-50 text-sky-800 border-sky-200/60';
        else if (art.status === '已通過') badgeClass = 'bg-emerald-50 text-emerald-800 border-emerald-200/60';

        return `
            <tr class="hover:bg-stone-50/50 transition-colors">
                <td class="px-6 py-4">
                    <div class="font-semibold text-stone-800 cursor-pointer hover:text-emerald-700 transition" onclick="openDetailModal(${art.id})">${escapeHtml(art.title)}</div>
                    <div class="text-xs text-stone-400 mt-1 line-clamp-1">${escapeHtml(art.content.substring(0, 45))}...</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2.5 py-1 text-xs font-medium rounded-lg bg-stone-100 text-stone-600">${art.category}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-3 py-1 inline-flex text-xs font-medium rounded-full border ${badgeClass}">
                        ${art.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-xs text-stone-400">
                    ${art.updated_at ? art.updated_at.replace('T', ' ').substring(0, 16) : '-'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-1.5">
                    <button onclick="openDetailModal(${art.id})" class="text-stone-400 hover:text-stone-700 p-2 rounded-xl hover:bg-stone-100 transition" title="檢視內容">
                        <i data-lucide="eye" class="w-4 h-4"></i>
                    </button>
                    ${art.status === '編輯中' ? `
                        <button onclick="openEditorModal(${art.id})" class="text-stone-600 hover:text-emerald-700 p-2 rounded-xl hover:bg-emerald-50 transition" title="編輯稿件">
                            <i data-lucide="edit-3" class="w-4 h-4"></i>
                        </button>
                        <button onclick="submitArticle(${art.id})" class="text-emerald-700 hover:text-emerald-900 p-2 rounded-xl hover:bg-emerald-50 transition" title="送出投稿">
                            <i data-lucide="send" class="w-4 h-4"></i>
                        </button>
                        <button onclick="deleteArticle(${art.id})" class="text-stone-400 hover:text-rose-600 p-2 rounded-xl hover:bg-rose-50 transition" title="刪除稿件">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
    }).join('');
    lucide.createIcons();
}

// Render Editor List
function renderEditorList() {
    const tbody = document.getElementById('editor-table-body');
    const emptyEl = document.getElementById('editor-empty');
    const pendingCountBadge = document.getElementById('pending-count-badge');

    let pendingArticles = articles.filter(art => art.status === '審查中');
    pendingCountBadge.innerText = `${pendingArticles.length} 篇`;

    if (pendingArticles.length === 0) {
        tbody.innerHTML = '';
        emptyEl.classList.remove('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    tbody.innerHTML = pendingArticles.map(art => {
        return `
            <tr class="hover:bg-stone-50/50 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap font-medium text-stone-800 text-xs">
                    一般作者
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2.5 py-1 text-xs font-medium rounded-lg bg-stone-100 text-stone-600">${art.category}</span>
                </td>
                <td class="px-6 py-4">
                    <div class="font-semibold text-stone-800 cursor-pointer hover:text-emerald-700 transition" onclick="openDetailModal(${art.id})">${escapeHtml(art.title)}</div>
                    <div class="text-xs text-stone-400 mt-1 line-clamp-1">${escapeHtml(art.content.substring(0, 45))}...</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-xs text-stone-400">
                    ${art.updated_at ? art.updated_at.replace('T', ' ').substring(0, 16) : '-'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button onclick="openDetailModal(${art.id})" class="text-stone-500 hover:text-stone-700 px-3 py-2 rounded-xl hover:bg-stone-100 transition inline-flex items-center space-x-1 text-xs">
                        <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                        <span>預覽</span>
                    </button>
                    <button onclick="reviewArticle(${art.id}, 'approve')" class="bg-emerald-700 hover:bg-emerald-800 text-white px-3.5 py-2 rounded-xl text-xs font-medium shadow-xs transition inline-flex items-center space-x-1">
                        <i data-lucide="check" class="w-3.5 h-3.5"></i>
                        <span>通過</span>
                    </button>
                    <button onclick="reviewArticle(${art.id}, 'reject')" class="bg-amber-100 hover:bg-amber-200 text-amber-900 px-3.5 py-2 rounded-xl text-xs font-medium transition inline-flex items-center space-x-1">
                        <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i>
                        <span>退回</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    lucide.createIcons();
}

// Open Add/Edit Modal
function openEditorModal(id = null) {
    const modal = document.getElementById('article-modal');
    const titleEl = document.getElementById('modal-title');
    document.getElementById('article-form').reset();
    document.getElementById('article-id').value = '';

    if (id) {
        const art = articles.find(a => a.id === id);
        if (art) {
            titleEl.innerHTML = `<i data-lucide="file-edit" class="w-4 h-4 text-emerald-700"></i><span>編輯投稿稿件</span>`;
            document.getElementById('article-id').value = art.id;
            document.getElementById('article-author').value = "作者";
            document.getElementById('article-category').value = art.category;
            document.getElementById('article-title').value = art.title;
            document.getElementById('article-content').value = art.content;
        }
    } else {
        titleEl.innerHTML = `<i data-lucide="file-edit" class="w-4 h-4 text-emerald-700"></i><span>新增投稿稿件</span>`;
    }

    modal.classList.remove('hidden');
    lucide.createIcons();
}

// Handle Form Submit (POST for create, PUT for update)
async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('article-id').value;
    const category = document.getElementById('article-category').value;
    const title = document.getElementById('article-title').value;
    const content = document.getElementById('article-content').value;
    const shouldSubmit = e.submitter?.value === 'submit';

    const payload = {
        title: title,
        category: category,
        content: content,
        status: "編輯中"
    };

    try {
        let response;
        if (id) {
            // 編輯
            response = await fetch(`${API_URL}/api/submissions/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // 新增
            response = await fetch(`${API_URL}/api/submissions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || '操作失敗');
        }

        const savedArt = await response.json();

        // 如果點擊「直接上傳」，則同步執行送審
        if (shouldSubmit && !id) {
            await fetch(`${API_URL}/api/submissions/${savedArt.id}/submit`, {
                method: 'POST'
            });
        }

        closeModal('article-modal');
        showToast('儲存成功');
        fetchSubmissions();
    } catch (error) {
        alert("錯誤：" + error.message);
    }
}

// 送出審查 (編輯中 -> 審查中)
async function submitArticle(id) {
    try {
        const response = await fetch(`${API_URL}/api/submissions/${id}/submit`, {
            method: 'POST'
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '送審失敗');
        }
        showToast('已成功送出審查');
        fetchSubmissions();
    } catch (error) {
        alert(error.message);
    }
}

// 刪除稿件
async function deleteArticle(id) {
    if (confirm('確定要刪除此稿件嗎？')) {
        try {
            const response = await fetch(`${API_URL}/api/submissions/${id}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || '刪除失敗');
            }
            showToast('稿件已刪除');
            fetchSubmissions();
        } catch (error) {
            alert(error.message);
        }
    }
}

// 編輯審查動作 (approve / reject)
async function reviewArticle(id, action) {
    try {
        const response = await fetch(`${API_URL}/api/submissions/${id}/review?action=${action}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '審查操作失敗');
        }
        closeModal('detail-modal');
        showToast(action === 'approve' ? '已審查通過' : '已退回稿件');
        fetchSubmissions();
    } catch (error) {
        alert(error.message);
    }
}

// 開啟詳細內容 Modal
function openDetailModal(id) {
    const art = articles.find(a => a.id === id);
    if (!art) return;

    document.getElementById('detail-title').innerText = art.title;
    document.getElementById('detail-author').innerText = "作者";
    document.getElementById('detail-category-badge').innerText = art.category;
    document.getElementById('detail-status-badge').innerText = art.status;
    document.getElementById('detail-date').innerText = art.updated_at ? art.updated_at.replace('T', ' ').substring(0, 16) : '-';
    document.getElementById('detail-content').innerText = art.content;

    const footerActions = document.getElementById('detail-footer-actions');
    if (currentRole === 'editor' && art.status === '審查中') {
        footerActions.innerHTML = `
            <button onclick="reviewArticle(${art.id}, 'reject')" class="bg-amber-100 hover:bg-amber-200 text-amber-900 px-4 py-2.5 rounded-2xl text-xs font-medium transition flex items-center space-x-1.5">
                <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
                <span>退回稿件</span>
            </button>
            <button onclick="reviewArticle(${art.id}, 'approve')" class="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2.5 rounded-2xl text-xs font-medium shadow-xs transition flex items-center space-x-1.5">
                <i data-lucide="check-circle" class="w-4 h-4"></i>
                <span>審查通過</span>
            </button>
        `;
    } else {
        footerActions.innerHTML = `
            <button onclick="closeModal('detail-modal')" class="bg-stone-200 hover:bg-stone-300 text-stone-700 px-5 py-2.5 rounded-2xl text-xs font-medium transition">關閉</button>
        `;
    }

    document.getElementById('detail-modal').classList.remove('hidden');
    lucide.createIcons();
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

function showToast(message) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    toastMessage.innerText = message;
    toast.classList.remove('translate-y-20', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');
    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}