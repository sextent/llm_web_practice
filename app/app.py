import os
import dashscope.audio
from flask import Flask, render_template, request, jsonify,url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from engineio.async_drivers import threading
from openai import OpenAI
from werkzeug.routing import BaseConverter
# 导入转换器的基类，用于继承方法
import sys
import signal
import dashscope
import pyaudio
from dashscope.audio.asr import *
from threading import Thread

mic = None
stream = None
recognition = None

# Set recording parameters
sample_rate = 16000  # sampling rate (Hz)
channels = 1  # mono channel
dtype = 'int16'  # data type
format_pcm = 'pcm'  # the format of the audio data
block_size = 3200  # number of frames per buffer

app = Flask(__name__)
CORS(app)  # 启用CORS支持
app.config['SECRET_KEY'] = '810975'
# Socket.IO允许服务器和客户端之间进行实时数据交换，
# 使得服务器可以实时地将数据推送到客户端，而无需客户端轮询服务器以获取更新。
# cors_allowed_origins='*'参数允许来自任何域名的WebSocket连接
socketio=SocketIO(app,cors_allowed_origins="*",async_mode='threading')

# app.config.form_object('settings')

# 当用户访问根路径（/）时，Flask将调用index()函数，并返回渲染后的网页。
@app.route('/')
def index():
    print('接收到访问请求')
    return render_template('index.html',title='语音识别')


# websocket事件处理
@socketio.on('start_recognition')
def handle_start_recognition():
    global recognition
    try:
        #初始化识别器
        callback = Callback()
        # Call recognition service by async mode, you can customize the recognition parameters, like model, format,
    # sample_rate For more information, please refer to https://help.aliyun.com/document_detail/2712536.html
        recognition = Recognition(
                model='paraformer-realtime-v2',
                format=format_pcm,
                sample_rate=sample_rate,
                semantic_punctuation_enabled=False,
                callback=callback,
            )
        recognition.start()
        def process_audio():
            while stream:
                try:
                    data = stream.read(block_size,exception_on_overflow=False)
                    recognition.send_audio_frame(data)
                except Exception as e:
                    print(f"Error sending audio: {e}")
                    break
        # 创建一个线程来处理音频数据
        audio_thread = Thread(target=process_audio, daemon=True)
        audio_thread.start()
        emit('recognition_started', {'message': '录音开始'})
    except Exception as e:
        emit('recognition_error', {'error': str(e)})
        print(f"Error starting recognition: {e}")
        
@socketio.on('stop_recognition')
def handle_stop_recognition():
    global recognition
    try:
        if recognition:
            recognition.stop()
            recognition = None
            emit('recognition_stopped', {'message': '录音结束'})
    except Exception as e:
        emit('recognition_error', {'error': str(e)})
        print(f"Error stopping recognition: {e}")
        
# method 参数用于指定允许的请求格式，这里设置为POST，表示只允许POST请求
# request.get_json()用于获取请求中的JSON数据
# 常规输入url的访问就是get方法，而ajax请求就是post方法
# 通过request.get_json()获取请求中的JSON数据，然后从中提取出需要翻译的文本和目标语言
# 使用googletrans进行翻译，将翻译结果返回给客户端
@app.route('/translate', methods=['POST'])
def translate():
    try:
        # 测试连接
        print("Testing API connection...")
        test_client =OpenAI(
            api_key='sk-6145dc5b48cf44728319e074f4c588f5',
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
        """
         # 进行一个简单的测试请求
        try:
            test_response = test_client.chat.completions.create(
                model='qwen-turbo',  # 使用 turbo 模型进行测试
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.3,
                stream=False
            )
            print(f"Test connection successful: {test_response}")
        except Exception as test_error:
            print(f"API connection test failed: {str(test_error)}")
            return jsonify({
                'success': False,
                'error': f"API connection failed: {str(test_error)}"
            }), 500
        """
        # 获取请求中的JSON数据
        data = request.get_json()
        text = data.get('text')
        print(f"Received text: {text}")
        target_lang = data.get('target_lang','zh')
        
        if not text or not target_lang:
            return jsonify({'error': 'Missing text or target language'}), 400
        
        # 初始化openai客户端
        client = OpenAI(
            api_key='sk-6145dc5b48cf44728319e074f4c588f5',
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
        # 构建翻译提示
        system_prompt = f"我是一个正在学习的数学系大学生，你的任务是尽可能详细地回答以下问题以给我学习上的帮助：{text},当你需要自我介绍的时候只要说明你是一个ai助手或助教即可。不应该包含你的模型和厂家。"
        #system_prompt = f"你是一个专业的翻译员，你的任务是将文本{text}翻译成{target_lang}语言。只需要输出翻译后的内容"
        print(f"System Prompt: {system_prompt}")  # 添加提示日志
        # 发送翻译请求
        response = client.chat.completions.create(
            model='qwen-turbo',
            messages=[
                {
                    "role": "user",
                    "content": system_prompt
                }
            ],
            temperature=0.3,
            modalities=['text'], # 只需要文本输出
            stream=False
        )
        print(f"API Response: {response}")  # 添加响应日志
        # 获取翻译结果
        translation = response.choices[0].message.content
        print(f"Translation: {translation}")
        # 返回翻译结果
        return jsonify({'success':True,
                        'original': text,
                        'translation': translation})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        error_message = str(e)
        if 'internal_error' in error_message:
            error_message = "服务暂时不可用，请稍后重试"
        return jsonify({
            'success': False,
            'error': error_message
        }), 500


def init_dashscope_api_key():
    """
        Set your DashScope API-key. More information:
        https://github.com/aliyun/alibabacloud-bailian-speech-demo/blob/master/PREREQUISITES.md
    """

    if 'DASHSCOPE_API_KEY' in os.environ:
        dashscope.api_key = os.environ[
            'DASHSCOPE_API_KEY']  # load API-key from environment variable DASHSCOPE_API_KEY
    else:
        dashscope.api_key = 'sk-6145dc5b48cf44728319e074f4c588f5'  # set API-key manually

# Real-time speech recognition callback
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print('RecognitionCallback open.')
        # 创建pyaudio实例
        mic = pyaudio.PyAudio()
        # 打开音频流
        stream = mic.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True)
        socketio.emit('recognition_status', {'status': 'started'})
        # Start recording
        

    def on_close(self) -> None:
        global mic
        global stream
        print('RecognitionCallback close.')
        stream.stop_stream()
        stream.close()
        # 释放PortAudio资源
        mic.terminate()
        stream = None
        mic = None

    def on_complete(self) -> None:
        print('RecognitionCallback completed.')  # translation completed

    def on_error(self, message) -> None:
        print('RecognitionCallback task_id: ', message.request_id)
        print('RecognitionCallback error: ', message.message)
        # Stop and close the audio stream if it is running
        if 'stream' in globals() and stream.active:
            stream.stop()
            stream.close()
        # Forcefully exit the program
        sys.exit(1)
    # 处理识别结果
    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        if 'text' in sentence:
            text=sentence['text']
            print('RecognitionCallback text: ', sentence['text'])
            socketio.emit('recognition_result',{'text':text})
            if RecognitionResult.is_sentence_end(sentence):
                print(
                    'RecognitionCallback sentence end, request_id:%s, usage:%s'
                    % (result.get_request_id(), result.get_usage(sentence)))

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global recognition
    try:
        if recognition:
            recognition.stop()
            print('Recognition stopped.')
        
        # 清理资源
        if 'stream' in globals() and stream:
            stream.stop_stream()
            stream.close()
        if 'mic' in globals() and mic:
            mic.terminate()
            
        return jsonify({'success': True, 'message': 'Server shutdown successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 定义一个信号处理函数，用于捕获Ctrl+C信号，停止翻译并退出程序
def signal_handler(sig, frame):
    print('按下Ctrl+C, 停止翻译 ...')
    global recognition
    try:
        if recognition:
            recognition.stop()
            print('Translation stopped.')
            print(
                '[Metric] requestId: {}, first package delay ms: {}, last package delay ms: {}'
                .format(
                    recognition.get_last_request_id(),
                    recognition.get_first_package_delay(),
                    recognition.get_last_package_delay(),
                ))
    except Exception as e:
        print(f"Error stopping recognition: {e}")
    finally:
        # 清理资源
        if 'stream' in globals() and stream:
            stream.stop_stream()
            stream.close()
        if 'mic' in globals() and mic:
            mic.terminate()
        sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 初始化API key
    init_dashscope_api_key()
    print('Initializing ...')
    
    try:
        socketio.run(app, host='0.0.0.0', port=9000, debug=True)
    except KeyboardInterrupt:
        # 当收到 Ctrl+C 时，触发信号处理
        signal_handler(signal.SIGINT, None)

    



