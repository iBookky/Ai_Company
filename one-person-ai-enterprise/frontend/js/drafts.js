/* ═══════════════════════════════════════
   drafts.js — Draft Repository
   ═══════════════════════════════════════ */

let currentCategory = '';
let pendingFile = null;

// ─── Load Drafts ──────────────────────────────────────────
async function loadDrafts() {
  const grid = document.getElementById('drafts-grid');
  grid.innerHTML = '<div class="loading-skeleton card"></div><div class="loading-skeleton card"></div>';

  try {
    const params = currentCategory ? `?category=${currentCategory}` : '';
    const drafts = await apiFetch(`/api/drafts${params}`);
    renderDraftsGrid(drafts);
    document.getElementById('stat-draft-count').textContent = drafts.length;
  } catch (e) {
    grid.innerHTML = `<div class="card" style="padding:2rem;color:var(--color-error)">โหลดไม่สำเร็จ: ${e.message}</div>`;
  }
}

function renderDraftsGrid(drafts) {
  const grid = document.getElementById('drafts-grid');

  if (!drafts || !drafts.length) {
    grid.innerHTML = `
      <div style="grid-column:1/-1">
        <div class="empty-state" style="min-height:250px">
          <span>📁</span>
          <p>ยังไม่มีเอกสารร่างในหมวดนี้</p>
          <label class="btn btn-primary" for="file-upload-input">⬆️ อัปโหลดเอกสาร</label>
        </div>
      </div>`;
    return;
  }

  grid.innerHTML = drafts.map(draft => `
    <div class="draft-card">
      <div class="draft-icon">${fileIcon(draft.content_type)}</div>
      <div class="draft-name">${esc(draft.name)}</div>
      <div class="draft-meta">
        <span>${formatFileSize(draft.size_bytes)}</span>
        <span>${formatDate(draft.uploaded_at)}</span>
      </div>
      <div style="font-size:11px;color:var(--color-text-muted)">${categoryLabel(draft.category)}</div>
      <div class="draft-actions">
        <button class="btn btn-sm btn-primary" onclick="viewDraft('${esc(draft.category)}', '${esc(draft.id)}')" title="ดูไฟล์">
          👁️ ดู
        </button>
        <button class="btn btn-sm" onclick="printDraft('${esc(draft.category)}', '${esc(draft.id)}', '${esc(draft.name)}')" title="พิมพ์">
          🖨️ พิมพ์
        </button>
        <button class="btn btn-sm btn-danger" onclick="deleteDraft('${esc(draft.category)}', '${esc(draft.id)}', '${esc(draft.name)}')" title="ลบ">
          🗑️
        </button>
      </div>
    </div>
  `).join('');
}

// ─── Category Filter ──────────────────────────────────────
function selectCategory(btn, cat) {
  currentCategory = cat;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const label = document.getElementById('drafts-category-label');
  label.textContent = cat ? categoryLabel(cat) : '';

  loadDrafts();
}

function categoryLabel(cat) {
  const labels = { proposals: '📄 ใบเสนอราคา', accounting: '📊 บัญชี', contracts: '📋 สัญญา' };
  return labels[cat] || cat;
}

// ─── Upload ───────────────────────────────────────────────
async function uploadDraft(input) {
  if (!input.files || !input.files[0]) return;
  pendingFile = input.files[0];

  // ถ้าเลือก category แล้วให้ถามผ่าน modal
  const modal = document.getElementById('upload-category-modal');
  if (currentCategory) {
    document.getElementById('upload-category-select').value = currentCategory;
  }
  modal.style.display = 'flex';
}

async function confirmUpload() {
  if (!pendingFile) return;
  const category = document.getElementById('upload-category-select').value;
  closeUploadModal();

  const formData = new FormData();
  formData.append('file', pendingFile);
  formData.append('category', category);

  showToast('⬆️ กำลังอัปโหลด...', 'info');

  try {
    const res = await fetch(`${API}/api/drafts/upload`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'อัปโหลดไม่สำเร็จ');
    }
    showToast(`อัปโหลด "${pendingFile.name}" สำเร็จ 🎉`, 'success');
    pendingFile = null;
    await loadDrafts();
  } catch (e) {
    showToast(`อัปโหลดไม่สำเร็จ: ${e.message}`, 'error');
  }

  // reset input
  const input = document.getElementById('file-upload-input');
  if (input) input.value = '';
}

function closeUploadModal() {
  document.getElementById('upload-category-modal').style.display = 'none';
}

// ─── View (Inline Preview) ────────────────────────────────
function viewDraft(category, fileId) {
  const url = `${API}/api/drafts/${category}/${fileId}/view`;
  window.open(url, '_blank');
}

// ─── Print ────────────────────────────────────────────────
function printDraft(category, fileId, fileName) {
  const url = `${API}/api/drafts/${category}/${fileId}/view`;
  const printWin = window.open(url, '_blank');

  if (printWin) {
    printWin.addEventListener('load', () => {
      setTimeout(() => {
        printWin.print();
      }, 800);
    });
    showToast(`เปิดหน้าพิมพ์ "${fileName}"`, 'info');
  } else {
    showToast('กรุณาอนุญาต popup เพื่อพิมพ์', 'warning');
  }
}

// ─── Delete ───────────────────────────────────────────────
async function deleteDraft(category, fileId, fileName) {
  if (!confirm(`ต้องการลบ "${fileName}" ใช่ไหม?`)) return;
  try {
    await apiFetch(`/api/drafts/${category}/${fileId}`, { method: 'DELETE' });
    showToast(`ลบ "${fileName}" สำเร็จ`, 'warning');
    await loadDrafts();
  } catch (e) {
    showToast(`ลบไม่สำเร็จ: ${e.message}`, 'error');
  }
}
