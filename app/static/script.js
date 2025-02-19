// static/script.js

// Socket.IO 连接和事件处理
const socket = io();
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const output = document.getElementById('output');
const status = document.getElementById('status');
const textInput = document.getElementById('textInput');
const translateBtn = document.getElementById('translateBtn');
const textOutput = document.getElementById('textOutput');

// Socket.IO 事件处理
socket.on('connect', () => {
    console.log('Connected to server');
    status.textContent = '已连接到服务器';
});

socket.on('recognition_status', (data) => {
    status.textContent = data.status === 'started' ? '正在录音...' : '录音已停止';
});

socket.on('recognition_result', (data) => {
    output.value += data.text + '\n';
    output.scrollTop = output.scrollHeight;
});

socket.on('recognition_error', (data) => {
    console.error('Error:', data.error);
    status.textContent = '错误: ' + data.error;
    startBtn.disabled = false;
    stopBtn.disabled = true;
});

// 语音识别按钮事件处理
function handleStartRecognition() {
    socket.emit('start_recognition');
    startBtn.disabled = true;
    stopBtn.disabled = false;
    output.value = '';
}

function handleStopRecognition() {
    socket.emit('stop_recognition');
    startBtn.disabled = false;
    stopBtn.disabled = true;
}

// 翻译功能
async function handleTranslation() {
    const text = textInput.value.trim();
    if (!text) {
        textOutput.value = '请输入要翻译的文本';
        return;
    }

    // 显示加载状态
    translateBtn.disabled = true;
    textOutput.value = '正在翻译...';

    try {
        const response = await fetch('/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                target_lang: 'zh'
            })
        });

        const data = await response.json();
        if (data.success) {
            textOutput.value = `原文：${data.original}\n译文：${data.translation}`;
        } else {
            textOutput.value = `翻译失败：${data.error || '请稍后重试'}`;
        }
    } catch (error) {
        console.error('Translation error:', error);
        textOutput.value = '翻译失败：网络错误，请稍后重试';
    } finally {
        translateBtn.disabled = false;
    }
}

// 事件监听器
document.addEventListener('DOMContentLoaded', () => {
    startBtn.addEventListener('click', handleStartRecognition);
    stopBtn.addEventListener('click', handleStopRecognition);
    translateBtn.addEventListener('click', handleTranslation);
});
