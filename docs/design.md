# 系统设计

## 1. 总体架构

```text
Browser (HTML/CSS/JS)
  │  MediaRecorder → Blob/File
  │  multipart/form-data: file + language
  ▼
FastAPI (app/main.py)
  ├── /health                 健康检查
  ├── /                       静态页面
  └── /api/transcribe         识别接口
        ├── audio.py          文件校验、时长探测
        ├── asr.py            faster-whisper 封装
        └── errors.py         统一错误映射
              ▼
本地模型缓存 models/（faster-whisper / CTranslate2 / CPU int8）
```

前端与后端通过 HTTP 交互，无数据库、无外部服务。模型只在首次使用时加载，后续请求复用单例。

## 2. 核心模块

| 模块 | 职责 |
| --- | --- |
| `app/main.py` | 路由、依赖注入、异常处理、静态文件挂载 |
| `app/config.py` | 从环境变量读取模型、上传、离线配置 |
| `app/audio.py` | 扩展名/大小校验，使用 PyAV 探测音频时长，临时文件管理 |
| `app/asr.py` | 懒加载模型单例，调用 `WhisperModel.transcribe`，拼接收集结果 |
| `app/errors.py` | 自定义异常及 HTTP 状态码 |
| `app/schemas.py` | 响应数据结构 |
| `static/app.js` | 录音、上传、状态机、结果渲染、复制、实时预览 |

## 3. 音频处理流程

1. 前端录音：
   - `getUserMedia({audio:true})` 获取麦克风。
   - `MediaRecorder` 选择 `audio/webm;codecs=opus`，不可用时回退 `audio/webm` / `audio/ogg`。
   - 录音中每秒更新计时，达到 60 秒自动调用 `stop()`。
2. 提交：
   - 录音 Blob 包装为 `File`，或直接使用用户选择的文件。
   - `FormData` 追加 `file` 与 `language`。
3. 后端：
   - 校验扩展名、非空、大小 ≤ 10 MB。
   - 用 PyAV 打开音频流并读取时长；无音频流或解码失败返回 400。
   - 写入带正确扩展名的临时文件，交给 faster-whisper 解码与推理。
   - 拼接 segments 的文本，返回 stripped 结果。
4. 计时：
   - `duration_seconds` 来自 PyAV 探测。
   - `processing_seconds` 从模型已加载后开始计时，覆盖解码+推理，不包含下载/加载时间。

## 4. 实时识别（F6，已实现）

前端提供 “Enable real-time preview” 复选框。开启后：

1. `MediaRecorder.start(4000)` 每 4 秒产生一个数据片段。
2. 每次收到片段后，把**目前为止积累的全部音频**作为快照提交 `/api/transcribe`。
3. 请求通过 Promise 链串行执行，避免乱序覆盖。
4. 返回的文本写入独立的 “Live transcript” 区域；停止录音后仍按完整音频提交一次，得到最终结果。

该方案不要求模型原生流式推理，符合需求文档中“允许通过短音频分片实现近实时识别”的说明。

## 5. ASR 模型选型

### 选择：faster-whisper（CTranslate2 后端）

- 默认模型：`small`，int8 量化，CPU 推理。
- 可选：低端机器通过 `ASR_MODEL_SIZE=base` 换取更快速度。
- 语言：`language="zh"` 或 `language="en"` 强制指定，不做翻译。
- 中文转写附加 `initial_prompt="请用简体中文转写普通话。"`，避免输出繁体中文。

### 选择理由

1. **本地与开源**：模型权重和推理库均可本地部署，无云端 API。
2. **CPU 友好**：CTranslate2 的 int8 量化在普通 CPU 上可用，无需 CUDA。
3. **中英文统一**：单个多语言模型覆盖两种语言，简化部署。
4. **安装简单**：pip 提供 Windows/macOS/Linux wheel，无需本地编译。
5. **成熟稳定**：API 清晰，便于用 Fake/Mock 做单元测试。

### 备选方案对比

| 方案 | 不选用的原因 |
| --- | --- |
| 原版 openai-whisper | 依赖 PyTorch，安装体积大，CPU 推理更慢 |
| Vosk | 中英文需不同模型，识别精度与标点表现较弱 |
| Web Speech API | 需求明确禁止 |
| 云端 ASR | 需求明确禁止 |
| whisper.cpp | 需要本地编译原生依赖，不符合统一复现要求 |

## 6. 离线策略

- 所有模型文件下载到 `ASR_MODEL_DIR`（默认 `./models`）。
- `LOCAL_FILES_ONLY=1` 时，向 `WhisperModel` 传入 `local_files_only=True`，彻底禁止联网检查。
- `scripts/fetch_model.py` 仅在联网环境执行一次，用于预下载。

## 7. 错误处理

| 场景 | 状态码 | 返回 |
| --- | --- | --- |
| 非法 language | 400 | 提示仅支持 zh/en |
| 缺少 file | 422 | FastAPI 参数校验 |
| 空文件 | 400 | 文件为空 |
| 无法解码 | 400 | 不是有效音频 |
| 不支持扩展名 | 415 | 格式不支持 |
| 超过 10 MB | 413 | 文件过大 |
| 模型加载/推理失败 | 500 | 可理解错误信息 |

前端捕获非 2xx 响应后读取 `detail` 并显示，同时恢复按钮状态，允许重试。

## 8. 测试设计

- 默认测试用 `FakeASRService` 覆盖 `get_asr_service`，不下载模型。
- `test_asr_service.py` 用 Mock 的 `WhisperModel` 验证语言参数、文本拼接和异常包装。
- `test_real_model.py` 用真实模型识别 `samples/` 下的中英文 WAV，默认跳过，通过 `-m real_model` 显式运行。
- 前端页面测试检查关键控件存在；浏览器录音/权限场景在测试报告中记录手动验证步骤。
