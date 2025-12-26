/**
 * LinearRAG Web Console - 前端应用
 */

// ==================== 全局状态 ====================
const state = {
    currentSection: 'dashboard',
    uploadedFile: null,
    datasets: [],
    queryCount: 0,
    pollInterval: null
};

// ==================== 工具函数 ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22,4 12,14.01 9,11.01"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showLoading(text = '处理中...') {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').textContent = text;
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(ms) {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}min`;
}

// ==================== 导航切换 ====================
function switchSection(sectionId) {
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === sectionId) {
            item.classList.add('active');
        }
    });
    
    // 更新内容区
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
    
    state.currentSection = sectionId;
    
    // 页面特定初始化
    if (sectionId === 'datasets') {
        loadDatasets();
    } else if (sectionId === 'pipeline') {
        loadUploadedDatasets();
    } else if (sectionId === 'query') {
        loadIndexedDatasets();
    }
}

// ==================== 系统状态 ====================
async function refreshStatus() {
    try {
        const [statusRes, progressRes] = await Promise.all([
            fetch('/api/status'),
            fetch('/api/progress')
        ]);
        
        const status = await statusRes.json();
        const progress = await progressRes.json();
        
        // 更新状态指示器
        const statusIndicator = document.getElementById('systemStatus');
        const statusText = document.getElementById('statusText');
        
        statusIndicator.classList.remove('error', 'warning');
        
        if (progress.status === 'error') {
            statusIndicator.classList.add('error');
            statusText.textContent = '处理出错';
        } else if (progress.status === 'running' || progress.status === 'indexing') {
            statusIndicator.classList.add('warning');
            statusText.textContent = progress.current_step || '处理中...';
        } else {
            statusText.textContent = '系统就绪';
        }
        
        // 更新统计
        document.getElementById('statDatasets').textContent = status.datasets_count || 0;
        document.getElementById('statQueries').textContent = state.queryCount;
        
        // 更新进度条
        document.getElementById('progressFill').style.width = `${progress.progress * 100}%`;
        document.getElementById('progressPercent').textContent = `${(progress.progress * 100).toFixed(0)}%`;
        document.getElementById('progressStep').textContent = progress.message || '等待任务...';
        
        return { status, progress };
    } catch (error) {
        console.error('获取状态失败:', error);
        return null;
    }
}

// ==================== 文件上传 ====================
function setupFileUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

function handleFileSelect(file) {
    if (!file.name.endsWith('.json')) {
        showToast('只支持JSON格式文件', 'error');
        return;
    }
    
    state.uploadedFile = file;
    
    document.getElementById('fileInfo').style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
}

function clearFile() {
    state.uploadedFile = null;
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('fileInput').value = '';
}

async function uploadFile() {
    const datasetName = document.getElementById('datasetName').value.trim();
    
    if (!datasetName) {
        showToast('请输入数据集名称', 'error');
        return;
    }
    
    if (!state.uploadedFile) {
        showToast('请选择要上传的文件', 'error');
        return;
    }
    
    showLoading('上传文件中...');
    
    try {
        const formData = new FormData();
        formData.append('file', state.uploadedFile);
        formData.append('dataset_name', datasetName);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`成功上传 ${result.chunks_count} 个文本块`, 'success');
            addToUploadHistory(result);
            clearFile();
            document.getElementById('datasetName').value = '';
        } else {
            showToast(result.detail || '上传失败', 'error');
        }
    } catch (error) {
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function addToUploadHistory(fileInfo) {
    const history = document.getElementById('uploadHistory');
    
    // 移除空状态
    const emptyState = history.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }
    
    const item = document.createElement('div');
    item.className = 'upload-item';
    item.innerHTML = `
        <div class="upload-item-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
            </svg>
        </div>
        <div class="upload-item-info">
            <div class="upload-item-name">${fileInfo.file_name}</div>
            <div class="upload-item-meta">${fileInfo.chunks_count} 个文本块 · ${formatFileSize(fileInfo.file_size)}</div>
        </div>
    `;
    
    history.insertBefore(item, history.firstChild);
}

// ==================== 流水线 ====================
async function loadUploadedDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const result = await response.json();
        
        const select = document.getElementById('pipelineDataset');
        select.innerHTML = '<option value="">请选择数据集...</option>';
        
        result.datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset;
            option.textContent = dataset;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载数据集列表失败:', error);
    }
}

async function startPipeline() {
    const datasetName = document.getElementById('pipelineDataset').value;
    
    if (!datasetName) {
        showToast('请选择数据集', 'error');
        return;
    }
    
    const config = {
        spacy_model: document.getElementById('spacyModel').value,
        llm_model: document.getElementById('llmModel').value,
        max_workers: parseInt(document.getElementById('maxWorkers').value),
        retrieval_top_k: parseInt(document.getElementById('retrievalTopK').value),
        max_iterations: parseInt(document.getElementById('maxIterations').value)
    };
    
    // 显示进度区域
    document.getElementById('pipelineProgress').style.display = 'block';
    document.getElementById('stopBtn').disabled = false;
    
    // 开始轮询进度
    startProgressPolling();
    
    try {
        const formData = new FormData();
        formData.append('dataset_name', datasetName);
        formData.append('config_data', JSON.stringify(config));
        
        showLoading('正在启动索引流水线...');
        
        const response = await fetch('/api/index', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('索引流水线已启动', 'success');
        } else {
            showToast(result.detail || '启动失败', 'error');
        }
    } catch (error) {
        showToast('启动失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function stopPipeline() {
    showToast('流水线程无法直接停止，将刷新状态', 'info');
    document.getElementById('stopBtn').disabled = true;
    stopProgressPolling();
}

function startProgressPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
    }
    
    updatePipelineProgress();
    
    state.pollInterval = setInterval(async () => {
        await updatePipelineProgress();
        
        // 检查是否完成
        const progress = await fetch('/api/progress').then(r => r.json());
        if (progress.status === 'completed' || progress.status === 'error') {
            stopProgressPolling();
            document.getElementById('stopBtn').disabled = true;
            
            if (progress.status === 'completed') {
                showToast('索引完成!', 'success');
            } else if (progress.status === 'error') {
                showToast('索引出错: ' + progress.message, 'error');
            }
        }
    }, 1000);
}

function stopProgressPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
}

async function updatePipelineProgress() {
    try {
        const progress = await fetch('/api/progress').then(r => r.json());
        
        // 更新所有步骤状态
        document.querySelectorAll('.step').forEach(step => {
            const stepName = step.dataset.step;
            step.classList.remove('active', 'completed');
            
            const statusSpan = step.querySelector('.step-status');
            
            if (progress.current_step === stepName) {
                step.classList.add('active');
                statusSpan.textContent = '进行中...';
            } else if (progress.status === 'completed' && stepName === 'completed') {
                step.classList.add('completed');
                statusSpan.textContent = '已完成';
            } else if (['loading_embedding', 'loading_llm', 'initializing', 'creating_rag', 'indexing'].includes(stepName)) {
                // 已完成的步骤
                const order = ['loading_embedding', 'loading_llm', 'initializing', 'creating_rag', 'indexing'];
                const currentIndex = order.indexOf(progress.current_step);
                const stepIndex = order.indexOf(stepName);
                
                if (stepIndex < currentIndex) {
                    step.classList.add('completed');
                    statusSpan.textContent = '已完成';
                }
            }
        });
        
        // 更新进度条
        const progressFill = document.getElementById('pipelineProgressFill');
        progressFill.style.width = `${progress.progress * 100}%`;
        
        // 更新进度文本
        document.getElementById('pipelineProgressText').textContent = 
            progress.message || '准备开始...';
        
        // 更新主进度条
        document.getElementById('progressFill').style.width = `${progress.progress * 100}%`;
        document.getElementById('progressPercent').textContent = `${(progress.progress * 100).toFixed(0)}%`;
        document.getElementById('progressStep').textContent = progress.message || '等待任务...';
        
    } catch (error) {
        console.error('更新进度失败:', error);
    }
}

// ==================== 在线查询 ====================
async function loadIndexedDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const result = await response.json();
        
        const select = document.getElementById('queryDataset');
        select.innerHTML = '<option value="">请选择已索引的数据集...</option>';
        
        result.datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset;
            option.textContent = dataset;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载数据集列表失败:', error);
    }
}

async function loadDataset(datasetName) {
    try {
        const response = await fetch(`/api/datasets/${datasetName}/load`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`已加载数据集: ${datasetName}`, 'success');
        } else {
            showToast(result.detail || '加载失败', 'error');
        }
    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    }
}

async function submitQuery() {
    const datasetName = document.getElementById('queryDataset').value;
    const question = document.getElementById('questionInput').value.trim();
    const topK = parseInt(document.getElementById('queryTopK').value);
    const useLLM = document.getElementById('useLLM').checked;
    
    if (!datasetName) {
        showToast('请选择数据集', 'error');
        return;
    }
    
    if (!question) {
        showToast('请输入问题', 'error');
        return;
    }
    
    const btn = document.getElementById('queryBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> 查询中...';
    
    try {
        // 确保数据集已加载
        await loadDataset(datasetName);
        
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                top_k: topK,
                use_llm: useLLM
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            state.queryCount++;
            document.getElementById('statQueries').textContent = state.queryCount;
            displayQueryResult(result);
        } else {
            showToast(result.error || '查询失败', 'error');
        }
    } catch (error) {
        showToast('查询失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            查询
        `;
    }
}

function displayQueryResult(result) {
    document.getElementById('queryResults').style.display = 'block';
    
    // 显示元信息
    const metaParts = [];
    if (result.retrieval_time_ms) {
        metaParts.push(`检索: ${formatTime(result.retrieval_time_ms)}`);
    }
    if (result.llm_time_ms) {
        metaParts.push(`LLM: ${formatTime(result.llm_time_ms)}`);
    }
    if (result.total_time_ms) {
        metaParts.push(`总计: ${formatTime(result.total_time_ms)}`);
    }
    document.getElementById('resultMeta').textContent = metaParts.join(' | ');
    
    // 显示答案
    const answerSection = document.getElementById('answerSection');
    if (result.answer) {
        answerSection.style.display = 'block';
        document.getElementById('answerContent').textContent = result.answer;
    } else {
        answerSection.style.display = 'none';
    }
    
    // 显示推理过程
    const thoughtSection = document.getElementById('thoughtSection');
    if (result.thought) {
        thoughtSection.style.display = 'block';
        document.getElementById('thoughtContent').textContent = result.thought;
    } else {
        thoughtSection.style.display = 'none';
    }
    
    // 显示检索到的文档
    const docsList = document.getElementById('docsList');
    docsList.innerHTML = '';
    
    result.retrieved_documents.forEach((doc, index) => {
        const docItem = document.createElement('div');
        docItem.className = 'doc-item';
        docItem.innerHTML = `
            <div class="doc-header">
                <span class="doc-score">#${index + 1} 相关度: ${(doc.score * 100).toFixed(1)}%</span>
            </div>
            <div class="doc-content">${escapeHtml(doc.content)}</div>
        `;
        docsList.appendChild(docItem);
    });
    
    // 滚动到结果
    document.getElementById('queryResults').scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 数据集管理 ====================
async function loadDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const result = await response.json();
        
        const list = document.getElementById('datasetsList');
        
        if (result.datasets.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    <p>暂无已索引的数据集</p>
                    <p class="hint">请先上传文件并执行索引流水线</p>
                </div>
            `;
            return;
        }
        
        list.innerHTML = '';
        
        result.datasets.forEach(dataset => {
            const item = document.createElement('div');
            item.className = 'dataset-item';
            item.innerHTML = `
                <div class="dataset-info">
                    <div class="dataset-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>
                    <div>
                        <div class="dataset-name">${dataset}</div>
                        <div class="dataset-meta">已索引</div>
                    </div>
                </div>
                <div class="dataset-actions">
                    <button class="btn btn-outline" onclick="loadDataset('${dataset}')" title="加载数据集">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17,8 12,3 7,8"/>
                            <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                        加载
                    </button>
                    <button class="btn-icon" onclick="deleteDataset('${dataset}')" title="删除数据集">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3,6 5,6 21,6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            `;
            list.appendChild(item);
        });
        
        document.getElementById('statDatasets').textContent = result.count;
        
    } catch (error) {
        console.error('加载数据集列表失败:', error);
        showToast('加载数据集列表失败', 'error');
    }
}

async function deleteDataset(datasetName) {
    if (!confirm(`确定要删除数据集 "${datasetName}" 吗？此操作不可恢复。`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/datasets/${datasetName}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('数据集已删除', 'success');
            loadDatasets();
            loadUploadedDatasets();
            loadIndexedDatasets();
        } else {
            showToast(result.detail || '删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    // 初始化导航
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchSection(item.dataset.section);
        });
    });
    
    // 初始化文件上传
    setupFileUpload();
    
    // 初始化刷新状态
    refreshStatus();
    
    // 定期刷新状态
    setInterval(refreshStatus, 5000);
    
    // 初始化查询输入框回车提交
    document.getElementById('questionInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            submitQuery();
        }
    });
    
    console.log('LinearRAG Web Console 已初始化');
});
