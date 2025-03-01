# LLM Web Practice

这是一个基于大语言模型(LLM)的Web应用实践项目。

## 项目说明

本项目旨在提供一个web服务平台，提供USTC——3DV项目组的LLM服务。同时也是作者的开发过程分享，希望能提供一个可参考的学习过程。

本项目集成了AI智能问答，数字人语音合成，数字人视频生成等功能。有语音和文本两种模态的交互过程。


## 安装

### 环境要求

- python >= 3.10

### 安装步骤

1. 克隆仓库
```bash
git clone [仓库地址]
cd llm_web_practice
```

2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 运行项目
```bash
python app.py
```
```bash
or
```
gunicorn -c gunicorn_config.py app.app:app