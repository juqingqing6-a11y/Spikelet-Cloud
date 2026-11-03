/* Batch controls: server-owned image URLs and recoverable progress updates. */
(function () {
    'use strict';
    const config = window.RGPAS_BATCH;
    let activeTask = null;
    let stream = null;
    let pollTimer = null;
    let lastResultCount = -1;
    let pollFailures = 0;
    let uploadConnectionLost = false;
    let waitingPolls = 0;

    function english() { return localStorage.getItem('language') === 'en'; }
    function message(zh, en) { return english() ? en : zh; }
    function closeProgress() {
        if (stream) { stream.close(); stream = null; }
        if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; }
    }
    function finish() {
        closeProgress();
        activeTask = null;
        $('#progressContainer').css('display', 'none');
        $('#button2').prop('disabled', false);
        $('#button1').prop('disabled', false);
        $('#model').prop('disabled', false);
        $('#folder').prop('disabled', false);
    }
    function renderRows(data) {
        if (Array.isArray(data.results) && data.results.length !== lastResultCount) {
            lastResultCount = data.results.length;
            window.updateResults(data);
        }
    }
    function applyProgress(data) {
        if (!activeTask || (data.task_id && data.task_id !== activeTask)) { return; }
        renderRows(data);
        if (data.status === 'queued') {
            $('#currentImageName').text(message('任务排队中…', 'Waiting for the server…'));
        } else if (data.current_file) {
            const count = data.index && data.total ? '(' + data.index + '/' + data.total + ')' : '';
            $('#currentImageName').text(message('正在处理', 'Processing') + count + ': ' + data.current_file);
        }
        if (data.done) {
            const failed = data.status === 'failed';
            finish();
            if (failed) { alert(data.error || message('处理失败。', 'Processing failed.')); }
        }
    }
    function startPolling() {
        if (!activeTask || pollTimer !== null) { return; }
        if (stream) { stream.close(); stream = null; }
        const task = activeTask;
        pollTimer = setTimeout(function poll() {
            pollTimer = null;
            if (activeTask !== task) { return; }
            $.ajax({
                url: config.statusUrl, type: 'GET', dataType: 'json',
                data: {task_id: task}, cache: false, timeout: 10000,
                success: function (data) {
                    if (activeTask !== task) { return; }
                    pollFailures = 0;
                    if (uploadConnectionLost && data.status === 'waiting') {
                        waitingPolls += 1;
                        if (waitingPolls >= 15) {
                            finish();
                            alert(message('无法找到该任务。请检查网络与代理，再重新提交。', 'The task could not be found. Check your network and proxy before submitting again.'));
                            return;
                        }
                    } else { waitingPolls = 0; }
                    applyProgress(data);
                },
                error: function (xhr) {
                    if (activeTask !== task) { return; }
                    if (xhr.status === 401) {
                        finish();
                        alert(message('登录已过期，请重新登录。', 'Please sign in again.'));
                    } else if (++pollFailures >= 5) {
                        finish();
                        alert(message('无法查询任务状态；任务可能仍在服务器执行。请检查代理后刷新页面。', 'Task status is unavailable; processing may still be running. Check your proxy and reload.'));
                    }
                },
                complete: function () {
                    if (activeTask === task) { startPolling(); }
                }
            });
        }, 2000);
    }
    function openProgress(task) {
        if (typeof EventSource === 'undefined') { startPolling(); return; }
        stream = new EventSource(config.progressUrl + '?task_id=' + encodeURIComponent(task));
        stream.onmessage = function (event) {
            try { applyProgress(JSON.parse(event.data)); }
            catch (_) { startPolling(); }
        };
        stream.onerror = function () {
            $('#currentImageName').text(message('进度连接中断，正在等待处理结果…', 'Progress connection interrupted; waiting for results…'));
            startPolling();
        };
    }
    window.getImage = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        if (activeTask) { return false; }
        const folder = document.getElementById('folder');
        const input = document.getElementById('file');
        const selected = input && input.files && input.files.length ? input.files : (folder && folder.files);
        const files = Array.from(selected || []).filter(function (file) {
            return /\.(jpe?g|png|bmp|tiff?|webp)$/i.test(file.name);
        });
        if (!files.length) {
            alert(message('请选择包含图片的文件夹。', 'Please select a folder containing images.'));
            return false;
        }
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrf) {
            alert(message('页面已失效，请刷新后重试。', 'Please reload the page and try again.'));
            return false;
        }
        activeTask = window.crypto && window.crypto.randomUUID ?
            window.crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);
        lastResultCount = -1;
        pollFailures = 0; waitingPolls = 0; uploadConnectionLost = false;
        window.updateResults({results: []});
        $('#button2').prop('disabled', true);
        $('#button1').prop('disabled', true);
        $('#model').prop('disabled', true);
        $('#folder').prop('disabled', true);
        $('#progressContainer').css('display', 'flex');
        $('#currentImageName').text(message('准备处理: ', 'Preparing: ') + files[0].name);
        const task = activeTask;
        const formData = new FormData();
        formData.append('task_id', task);
        formData.append('model', $('select[name=YOLO]').val());
        files.forEach(function (file) { formData.append('file', file); });
        openProgress(task);
        $.ajax({
            url: config.analyseUrl, type: 'POST', data: formData,
            processData: false, contentType: false, dataType: 'json',
            headers: {'X-CSRFToken': csrf.value},
            success: function (data) {
                if (activeTask !== task) { return; }
                renderRows(data);
                finish();
                if (data.error) { alert(data.error); }
            },
            error: function (xhr) {
                if (activeTask !== task) { return; }
                if (xhr.status === 0) {
                    uploadConnectionLost = true;
                    $('#currentImageName').text(message('连接中断，正在查询任务状态…', 'Connection interrupted; checking task status…'));
                    startPolling();
                    return;
                }
                let data = xhr.responseJSON;
                if (!data) {
                    try { data = JSON.parse(xhr.responseText); } catch (_) {}
                }
                if (data) { renderRows(data); }
                finish();
                alert(data && data.error || message('处理失败，请查看服务器日志。', 'Processing failed; please check the server log.'));
            }
        });
        return false;
    };
    $('#summer').on('submit', function (event) {
        event.preventDefault();
        window.getImage(event);
    });
}());
