/* Single-image transport. Keep the original IDs/forms; consume server URLs. */
(function () {
    'use strict';
    const get = id => document.getElementById(id);
    const form = get('options-form'), upload = get('form1'), extract = get('birthday');
    if (!form || !upload || !extract) { return; }
    const fileInput = upload.querySelector('input#file.filepath');
    const model = get('model'), countButton = get('btn'), extractButton = extract.querySelector('button[type=submit]');
    const routes = {count: form.dataset.singleCountUrl, extract: extract.dataset.singleExtractUrl};
    const state = {file: null, filename: '', analysis: null, counted: false, extracted: false, pending: null, reading: false};
    const pendingKey = 'rgpas-single-pending-v1', contextKey = 'rgpas-single-context-v1';
    let timer, generation = 0, localURL;
    const english = () => localStorage.getItem('language') === 'en';
    const text = (zh, en) => english() ? en : zh;
    const phases = {queued: ['等待计算资源', 'Waiting for compute'], initializing: ['初始化', 'Initializing'],
        detecting: ['正在计数', 'Counting'], classifying: ['正在分类', 'Classifying'],
        filtering: ['正在筛选', 'Filtering'], traits: ['正在计算表型', 'Calculating traits']};
    const store = (key, value) => { try { if (value) { sessionStorage.setItem(key, JSON.stringify(value)); } else { sessionStorage.removeItem(key); } } catch (_) {} };
    const load = key => { try { return JSON.parse(sessionStorage.getItem(key)); } catch (_) { return null; } };
    function id() {
        const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
        return Array.from(bytes, n => n.toString(16).padStart(2, '0')).join('');
    }
    function lock() {
        const busy = !!state.pending || state.reading;
        fileInput.disabled = busy; model.disabled = busy;
        countButton.disabled = busy || !state.file;
        extractButton.disabled = busy || !state.counted;
        get('button1').disabled = busy || !state.extracted;
        get('summary').textContent = state.pending && state.pending.kind === 'count' ? text('计数中…', 'Counting…') : text('穗粒计数', 'Grain detection');
        get('sort').textContent = state.pending && state.pending.kind === 'extract' ? text('正在提取…', 'Extracting…') : text('完整粒提取', 'Complete extraction');
    }
    function notice(message) { const node = get('completey'); node.style.lineHeight = '1.6'; node.textContent = message; }
    function clearResults() {
        state.analysis = null; state.counted = false; state.extracted = false;
        get('result').textContent = ''; get('compeleteSum').textContent = ''; get('pic').replaceChildren();
        notice(text('请先计数，再提取完整穗粒。', 'Count first, then extract whole grains.'));
        get('loadCSV').style.display = 'none'; store(contextKey, null);
    }
    function safeURL(value) {
        const url = new URL(value, location.origin);
        if (url.origin !== location.origin || !url.pathname.startsWith('/static/')) { throw new Error(text('结果图片地址无效。', 'Invalid result image URL.')); }
        return url.href;
    }
    function showOriginal(url) {
        get('img_upload_show').src = url; get('img_upload_show').alt = state.filename;
        get('img_upload_show').style.display = 'block'; get('add').style.display = 'none';
        get('myDiv').removeAttribute('disabled');
        const label = document.createElement('label'); label.htmlFor = 'file'; label.textContent = text('1. 重新上传图片', '1. Re-upload an image');
        label.style.cssText = 'margin:0;padding:6px 10px;background:#3888c7;color:white;border-radius:5px;cursor:pointer';
        get('rechoice').replaceChildren(label);
    }
    function renderCount(data) {
        if (!data.analysis_id || !data.result_url || !Number.isInteger(Number(data.image_number))) { throw new Error(text('计数响应不完整，请确认服务器已加载补丁。', 'Incomplete result. Check the server update.')); }
        state.analysis = data; state.counted = true; state.extracted = false; state.filename = data.filename;
        model.value = data.model; get('result').textContent = data.image_number;
        const image = document.createElement('img'); image.src = safeURL(data.result_url); image.alt = data.filename;
        image.style.cssText = 'width:298px;height:100%;cursor:pointer';
        image.addEventListener('click', () => { get('modalImage').src = image.src; get('imageModal').style.display = 'block'; });
        get('pic').replaceChildren(image); showOriginal(safeURL(data.original_url));
        get('savg').style.display = 'block'; get('ssv').style.display = 'block';
        store(contextKey, data);
    }
    function renderExtract(data) {
        if (!state.analysis || data.analysis_id !== state.analysis.analysis_id || !Array.isArray(data.complete_urls) || !Number.isInteger(Number(data.sum))) { throw new Error(text('提取响应与当前图片不一致。', 'Extraction does not match this image.')); }
        state.extracted = true; get('compeleteSum').textContent = String(data.sum);
        const container = get('completey'); container.replaceChildren(); container.style.lineHeight = '1.6'; container.style.marginTop = '10px';
        data.complete_urls.forEach((url, n) => {
            const image = document.createElement('img'); image.src = safeURL(url); image.alt = text('完整穗粒 ', 'Whole grain ') + (n + 1);
            image.style.cssText = 'width:auto;height:70px;margin:3px;object-fit:contain';
            image.addEventListener('error', () => { image.alt = text('图片加载失败，请刷新或检查网络', 'Image failed to load. Refresh or check the connection.'); });
            container.append(image);
        });
        if (!data.complete_urls.length) { notice(text('未找到完整穗粒。', 'No whole grains found.')); }
        get('ssssv').style.display = 'block'; get('loadCSV').style.display = 'block';
    }
    function finish(data, error) {
        clearTimeout(timer); state.pending = null; store(pendingKey, null);
        if (error) { notice(error); }
        else if (data.kind === 'count') { renderCount(data); notice(text('计数完成，可提取完整穗粒。', 'Counting complete. Whole-grain extraction is available.')); }
        else { renderExtract(data); }
        lock();
    }
    async function request(url, options) {
        const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 30000);
        try {
            const response = await fetch(url, {...options, signal: controller.signal, credentials: 'same-origin', cache: 'no-store'});
            let data;
            try { data = await response.json(); } catch (_) { throw new Error(text('代理或服务返回了非JSON响应。', 'The proxy or server returned a non-JSON response.')); }
            if (!response.ok) { const failure = new Error(data.error || data.message || ('HTTP ' + response.status)); failure.status = response.status; throw failure; }
            return data;
        } finally { clearTimeout(timeout); }
    }
    function retryNotice(message, pending) {
        notice(message);
        const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = text('重新查询原任务', 'Check the original task');
        retry.addEventListener('click', () => { pending.failures = 0; pending.missing = 0; poll(pending, generation); });
        get('completey').append(document.createElement('br'), retry);
        // Keep controls locked: a broken connection does not cancel server work.
    }
    function schedule(pending, token) { clearTimeout(timer); timer = setTimeout(() => poll(pending, token), 1500); }
    function accept(data, pending, token) {
        if (token !== generation || state.pending !== pending) { return; }
        if (data.task_id) { pending.id = data.task_id; store(pendingKey, pending); }
        if (data.done) {
            if (data.status !== 'finished') { finish(null, data.error || text('任务失败，请查看服务器日志。', 'Task failed. Check server logs.')); }
            else { try { finish(data); } catch (error) { state.counted = false; state.extracted = false; finish(null, error.message); } }
            return;
        }
        const phase = phases[data.phase] || phases.initializing;
        notice(phase[english() ? 1 : 0] + ' ' + (Number(data.progress) || 0) + '%');
        schedule(pending, token);
    }
    async function poll(pending, token) {
        if (token !== generation || state.pending !== pending) { return; }
        const url = new URL(routes[pending.kind], location.origin); url.searchParams.set('task_id', pending.id);
        if (pending.analysis_id) { url.searchParams.set('analysis_id', pending.analysis_id); }
        try { const data = await request(url.href); pending.failures = 0; pending.missing = 0; accept(data, pending, token); }
        catch (error) {
            if (token !== generation || state.pending !== pending) { return; }
            if (error.status === 401) { finish(null, error.message); return; }
            if (error.status === 404) {
                pending.missing = (pending.missing || 0) + 1;
                if (pending.missing >= 10) { state.counted = false; state.extracted = false; finish(null, error.message); return; }
            } else { pending.failures = (pending.failures || 0) + 1; }
            if (pending.failures >= 6) { retryNotice(text('任务状态暂时无法读取，后台可能仍在处理。请恢复网络后查询原任务。', 'Status is unavailable; the server may still be working. Restore the connection and check the original task.'), pending); return; }
            schedule(pending, token);
        }
    }
    async function start(kind, body) {
        const pending = {id: id(), kind, analysis_id: state.analysis && state.analysis.analysis_id, context: state.analysis, failures: 0, missing: 0};
        body.append('task_id', pending.id);
        state.pending = pending; const token = ++generation; store(pendingKey, pending); lock();
        notice(text('正在提交任务…', 'Submitting task…'));
        const csrf = form.querySelector('input[name=csrfmiddlewaretoken]');
        try { const data = await request(routes[kind], {method: 'POST', body, headers: csrf ? {'X-CSRFToken': csrf.value} : {}}); accept(data, pending, token); }
        catch (error) {
            if (token !== generation || state.pending !== pending) { return; }
            if (error.status && error.status < 500) { finish(null, error.message); return; }
            // The response may be lost after the server accepted this ID. Never POST again automatically.
            notice(text('提交连接中断，正在查询原任务…', 'Submission connection interrupted. Checking the original task…'));
            schedule(pending, token);
        }
    }
    form.addEventListener('submit', event => {
        event.preventDefault(); if (state.pending || state.reading) { return; }
        if (!state.file) { notice(text('请先选择图片。', 'Choose an image first.')); return; }
        clearResults(); state.filename = state.file.name;
        const data = new FormData(form); data.set('model', model.value); data.set('file', state.file);
        start('count', data);
    });
    extract.addEventListener('submit', event => {
        event.preventDefault(); if (state.pending || state.reading) { return; }
        if (!state.counted || !state.analysis || model.value !== state.analysis.model) { notice(text('请先完成当前图片和模型的计数。', 'Count the current image and model first.')); return; }
        state.extracted = false; get('loadCSV').style.display = 'none'; get('compeleteSum').textContent = '';
        const data = new FormData(extract); data.set('model', state.analysis.model); data.set('file', state.analysis.filename); data.set('analysis_id', state.analysis.analysis_id);
        start('extract', data);
    });
    function restoreFile() { const transfer = new DataTransfer(); if (state.file) { transfer.items.add(state.file); } fileInput.files = transfer.files; }
    function selectFile(event) {
        if (state.pending || state.reading) { restoreFile(); return; }
        const file = event && event.target.files[0]; if (!file) { restoreFile(); return; }
        state.reading = true; lock();
        const url = URL.createObjectURL(file), image = new Image();
        image.onload = () => {
            if (localURL) { URL.revokeObjectURL(localURL); } localURL = url;
            state.file = file; state.filename = file.name; state.reading = false; clearResults();
            model.value = model.options[0].value; showOriginal(url); get('mySvg').style.display = 'block'; lock();
        };
        image.onerror = () => { URL.revokeObjectURL(url); state.reading = false; restoreFile(); notice(text('无法读取图片，请选择有效的图片文件。', 'Unable to read this image. Choose a valid image file.')); lock(); };
        image.src = url;
    }
    model.addEventListener('change', () => { if (state.pending) { return; } clearResults(); lock(); });
    async function downloadCSV(event) {
        if (event) { event.preventDefault(); }
        if (!state.extracted || state.pending) { return; }
        const query = '?analysis_id=' + encodeURIComponent(state.analysis.analysis_id);
        try {
            const metadata = await request('/getLatestDetection/' + query);
            const response = await fetch('/downloadSingle/' + query, {credentials: 'same-origin', cache: 'no-store'});
            if (!response.ok) { throw new Error(text('CSV下载失败，请重新登录或检查服务器日志。', 'CSV download failed. Sign in again or check server logs.')); }
            const blob = await response.blob(), url = URL.createObjectURL(blob), link = document.createElement('a');
            link.href = url; link.download = metadata.pic.replace(/\.[^.]+$/, '') + '_grain_analysis.csv';
            document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) { notice(error.message); }
    }
    window.rgSingleAnalysis = {selectFile, downloadCSV};
    get('trait_div').addEventListener('submit', event => event.preventDefault());
    document.addEventListener('click', event => { if (event.target.closest('#chinese,#english')) { setTimeout(lock, 0); } });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') { get('imageModal').style.display = 'none'; } });
    get('loadCSV').style.display = 'none'; clearResults();
    const pending = load(pendingKey);
    if (pending && routes[pending.kind]) {
        if (pending.context) { state.analysis = pending.context; state.counted = true; state.filename = pending.context.filename; model.value = pending.context.model; showOriginal(safeURL(pending.context.original_url)); }
        state.pending = pending; lock(); poll(pending, ++generation);
    } else {
        // Completed results are deliberately not restored from unverified browser storage.
        lock();
    }
}());
