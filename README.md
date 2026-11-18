# Local Speech to Text

一个基于 **FastAPI + 本地 faster-whisper 模型** 的语音识别 Web 系统。浏览器录制麦克风音频或上传音频文件，后端在本地 CPU 上完成中英文识别，并把文字返回页面。

- 不调用任何云端 ASR API
- 不使用浏览器 Web Speech Recognition API
- CPU 即可运行，不要求 GPU / CUDA
- 模型准备完成后可完全离线识别

## 1. 环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 11 x64（也支持 macOS / Linux） |
| Python | 3.12（开发环境也可使用 3.10+） |
| 浏览器 | 最新稳定版 Chrome 或 Edge |
| 网络 | 仅首次下载模型权重时需要 |

## 2. 安装与启动

在 Windows 11 的 PowerShell / CMD 中：

```powershell
python -m pip install -r requirements.txt
python scripts/fetch_model.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

然后打开：

```text
http://127.0.0.1:8000
```

> `scripts/fetch_model.py` 只需要在首次安装或换模型时运行一次，用于下载模型权重到 `models/` 目录。该目录已加入 `.gitignore`，不需要提交。
>
> 如果无法访问 `huggingface.co`，可先设置镜像再下载：
>
> ```powershell
> $env:HF_ENDPOINT="https://hf-mirror.com"
> python scripts/fetch_model.py
> ```

## 3. 离线运行

模型下载完成后，可以强制后端只从本地缓存加载：

```powershell
# Windows PowerShell
$env:LOCAL_FILES_ONLY="1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# macOS / Linux
export LOCAL_FILES_ONLY=1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 4. 配置项

通过环境变量配置：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ASR_MODEL_SIZE` | `small` | 模型大小：`tiny` / `base` / `small` 等 |
| `ASR_MODEL_DIR` | `models` | 模型缓存目录 |
| `ASR_DEVICE` | `cpu` | 推理设备 |
| `ASR_COMPUTE_TYPE` | `int8` | 量化类型，CPU 推荐 `int8` |
| `ASR_CPU_THREADS` | `0` | CPU 线程数，`0` 表示自动 |
| `LOCAL_FILES_ONLY` | `0` | `1` 时禁止联网下载模型 |
| `MAX_UPLOAD_BYTES` | `10485760` | 上传文件大小上限（10 MB） |

## 5. 使用方式

1. 在页面选择识别语言：`中文（普通话）` 或 `English`。
2. 点击 **Start Recording** 授权麦克风并开始录音；最长 60 秒，到时自动停止。
3. 可选：勾选 **Enable real-time preview**，录音过程中每 4 秒刷新一次实时文字预览。
4. 点击 **Stop Recording** 后提交最终识别。
5. 或者选择一个 WAV / WebM / OGG 等音频文件，点击 **Upload & Transcribe**。
6. 识别结果显示在文本框中，可点击 **Copy** 复制。
7. 页面同时展示音频时长和服务端处理耗时。

## 6. HTTP 接口

| Method | Endpoint | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{"status":"ok"}` |
| GET | `/` | Web 页面 |
| POST | `/api/transcribe` | multipart 上传 `file` 与 `language`（`zh` / `en`） |

成功响应：

```json
{
  "text": "你好，欢迎使用本地语音识别系统。",
  "language": "zh",
  "duration_seconds": 6.25,
  "processing_seconds": 2.14
}
```

错误响应使用 `{"detail": "..."}`，并按需返回 400 / 413 / 415 / 500。

## 7. 测试

### 默认自动化测试（Mock，不下载模型）

```bash
python -m pytest -q
```

覆盖健康检查、正常/非法请求、音频校验、语言参数、错误处理、前端页面和模型调用 Mock。

### 真实模型测试

先运行一次 `python scripts/fetch_model.py`，然后：

```bash
python -m pytest -q -m real_model -o addopts=""
```

该测试使用 `samples/chinese.wav` 和 `samples/english.wav`，验证真实本地模型的中英文识别。

## 8. 项目结构

```text
.
├── app/            # FastAPI 后端、ASR 封装、音频处理
├── static/         # 原生 HTML/CSS/JS 前端
├── scripts/        # 模型下载脚本
├── tests/          # pytest 自动化测试
├── samples/        # 中英文测试音频与参考文本
├── docs/           # 需求、设计、测试报告、AI 开发记录与 OpenCode 过程证据
├── requirements.txt
├── pytest.ini
└── README.md
```

## 9. 已知限制

- 一次录音最长 60 秒；单文件上传上限 10 MB。
- 实时预览是近实时（约 4 秒刷新），不是严格的流式识别。
- 默认使用 `small` 模型以兼顾中文准确率与 CPU 速度；低端机器可设 `ASR_MODEL_SIZE=base` 换取更快速度。
