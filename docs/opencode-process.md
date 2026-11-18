# OpenCode 开发过程记录（关键会话证据）

> 说明：本文是 `docs/ai-development.md` 的补充证据材料，摘录了本次开发中的关键会话、命令输出和代码生成结果。内容已脱敏，不含个人信息、密钥或内部系统地址。完整历史对话未提交。

---

## 阶段一：需求理解与技术设计

### 1.1 让 OpenCode 阅读需求文档

**会话摘录**

> 用户：现在当前目录下有一需求文档.md，你按照需求文档进行项目的开发。你可以需求分析、任务拆分、方案设计、代码生成、测试及问题修复。
>
> OpenCode：已读完 `需求文档.md`。当前目录里只有这份需求文档，项目还没有任何代码。下面先给出**需求理解 + 方案设计 + 任务拆分 + 测试计划**。
>
> OpenCode：注意：我现在处于 **Plan 模式**，只能和你讨论方案，不能创建/修改文件。确认方案后，请切换到实现类 agent，我再按计划落地代码、测试和文档。

**产出**：`docs/requirements.md`

OpenCode 从需求文档中提取了 F1–F5 必做功能和 F6 加分功能，并明确了边界条件：

- 录音最长 60 秒
- 上传文件上限 10 MB
- 只允许 `zh` / `en` 两种语言
- 模型必须本地运行，CPU 必须支持
- 禁止 Web Speech API 和云端 ASR

### 1.2 让 OpenCode 选择 ASR 模型并制定方案

**会话摘录**

> OpenCode：推荐：**faster-whisper + CTranslate2（int8，CPU）**
>
> - 默认模型：`base`（约 140MB 权重，CPU 上速度较快）
> - 可选模型：通过环境变量 `ASR_MODEL_SIZE=small` 切换到更高精度
> - 理由：
>   - 开源、本地推理，满足禁止云端 API 的要求
>   - 原生支持 CPU int8，不强制 GPU/CUDA
>   - 不需要本地编译特殊原生依赖，Windows/macOS/Linux 都有 pip wheel
>   - 中英文同一个模型即可覆盖，比维护两套 Vosk 模型更简单
>   - 相比原版 `openai-whisper`，不需要 PyTorch，安装更轻、CPU 更快

**备选方案对比（由 OpenCode 生成）**

| 方案 | 不选用的原因 |
| --- | --- |
| 原版 openai-whisper | 依赖 PyTorch，安装体积大，CPU 推理更慢 |
| Vosk | 中英文需不同模型，识别精度与标点表现较弱 |
| Web Speech API | 需求明确禁止 |
| 云端 ASR | 需求明确禁止 |
| whisper.cpp | 需要本地编译原生依赖，不符合统一复现要求 |

### 1.3 任务拆分

OpenCode 给出的四阶段计划：

1. **阶段 1**：后端骨架 + 接口 + Mock 测试
2. **阶段 2**：前端录音、上传与结果展示
3. **阶段 3**：真实模型集成 + 样本 + 文档
4. **阶段 4**：加分功能 F6 实时识别

**产出**：`docs/design.md`、`README.md` 初稿

---

## 阶段二：功能开发与集成

### 2.1 用户确认方案

**会话摘录**

> 用户：好的，我觉得你的方案可以，开干吧

随后 OpenCode 切换到实现流程，开始创建文件。

### 2.2 OpenCode 生成的主要文件

| 文件 | 用途 |
| --- | --- |
| `app/main.py` | FastAPI 路由、依赖注入、异常处理、静态页面挂载 |
| `app/config.py` | 环境变量配置 |
| `app/audio.py` | 上传校验、时长探测、临时文件 |
| `app/asr.py` | faster-whisper 封装 |
| `app/errors.py` | 自定义异常 |
| `app/schemas.py` | 响应模型 |
| `static/index.html` / `styles.css` / `app.js` | Web 前端 |
| `scripts/fetch_model.py` | 模型预下载脚本 |
| `tests/` | pytest 自动化测试 |
| `samples/` | 中英文测试音频 |

### 2.3 关键代码生成结果

**后端 API（OpenCode 生成，摘自 `app/main.py`）**

```python
@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(...),
    service: ASRService = Depends(get_asr_service),
) -> TranscriptionResponse:
    if language not in settings.allowed_languages:
        raise InvalidLanguageError()

    data = await file.read()
    suffix = validate_upload(file.filename or "", data)
    duration_seconds = probe_audio(data, suffix)
    try:
        text, processing_seconds = service.transcribe(data, suffix, language)
    except AppError:
        raise
    except Exception as exc:
        raise ModelError("Speech recognition failed while processing the audio.") from exc
```

**模型集成（OpenCode 生成，摘自 `app/asr.py`）**

```python
transcribe_kwargs = {
    "language": language,
    "beam_size": 5,
    "condition_on_previous_text": False,
    "vad_filter": False,
}
if language == "zh":
    transcribe_kwargs["initial_prompt"] = "请用简体中文转写普通话。"

with temp_audio_file(data, suffix) as path:
    segments, _info = model.transcribe(path, **transcribe_kwargs)
    text = "".join(segment.text for segment in segments).strip()
```

**前端录音（OpenCode 生成，摘自 `static/app.js`）**

```javascript
recorder.ondataavailable = (event) => {
  if (event.data && event.data.size > 0) chunks.push(event.data);
  if (live && chunks.length > 0) {
    submitLiveSnapshot(recorderMimeType, extensionFromMime(recorderMimeType));
  }
};

recorder.onstop = async () => {
  stopTimer();
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  recorder = null;
  const blob = new Blob(chunks, { type: recorderMimeType || "audio/webm" });
  chunks = [];
  await submitAudio(blob, extensionFromMime(recorderMimeType), "recording");
};
```

### 2.4 测试音频生成

OpenCode 使用 macOS `say` 本地生成样本，避免版权问题：

```bash
say -v Tingting --data-format=LEI16@16000 -o samples/chinese.wav \
  '你好，欢迎使用本地语音识别系统。这是一段用于测试的中文语音。'

say -v Fred --data-format=LEI16@16000 -o samples/english.wav \
  'Hello, welcome to the local speech to text system. This is a short English test recording.'
```

输出时长：

```text
6.252500
6.647250
```

---

## 阶段三：测试与问题修复

### 3.1 第一次自动化测试：发现测试代码问题

**执行命令**

```bash
.venv/bin/python -m pytest -q
```

**实际输出（失败）**

```text
F..................                                                      [100%]
________________ test_service_returns_joined_text_and_language _________________
    assert model.kwargs["device"] == "cpu"
E   KeyError: 'device'
1 failed, 18 passed, 2 deselected in 0.41s
```

**OpenCode 定位过程**

> 原因：测试里用 `lambda *a, **k: model` 替换 `WhisperModel`，但没有真正调用 `FakeWhisperModel(*a, **k)`，所以构造函数参数没有被记录。
>
> 修复：改为工厂函数创建 Fake 实例并保存引用：
>
> ```python
> created = {}
>
> def factory(*args, **kwargs):
>     created["model"] = FakeWhisperModel(*args, **kwargs)
>     return created["model"]
>
> monkeypatch.setattr(asr_module, "WhisperModel", factory)
> ```

**修复后输出**

```text
...................                                                      [100%]
19 passed, 2 deselected in 0.05s
```

### 3.2 模型下载失败与网络修复

**执行命令**

```bash
.venv/bin/python scripts/fetch_model.py
```

**错误输出（节选）**

```text
httpcore2.ConnectError: [Errno 54] Connection reset by peer
huggingface_hub.errors.LocalEntryNotFoundError: Got: ConnectError: [Errno 54] Connection reset by peer
```

**OpenCode 处理**

> 改用 HuggingFace 镜像重试：
>
> ```bash
> HF_ENDPOINT=https://hf-mirror.com .venv/bin/python scripts/fetch_model.py
> ```

**成功输出**

```text
Downloading model 'base' to /Users/wangjp/aicode/Speech-to-Text/models ...
Model is ready. You can now run the server offline with LOCAL_FILES_ONLY=1.
```

### 3.3 真实模型精度问题与 AI 生成结果调整

**第一次真实模型测试（`base`）**

```bash
.venv/bin/python -m pytest -q -m real_model -o addopts=""
```

```text
2 passed in 1.79s
```

虽然测试通过，但中文输出存在错字：

```text
你好,欢迎使用本地余音时别系统,这是一段用于测试的中文余音。
```

**OpenCode 分析与调整**

> `base` 模型速度更快（中文 0.612s），但中文准确率不足。改用 `small` 模型后文字正确，但输出繁体：
>
> ```text
> 你好,歡迎使用本地語音識別系統,這是一段用於測試的中文語音。
> ```
>
> 因此增加简体中文提示词，并把默认模型改为 `small`：
>
> ```python
> transcribe_kwargs["initial_prompt"] = "请用简体中文转写普通话。"
> ```

**调整后真实输出**

```text
你好,欢迎使用本地语音识别系统,这是一段用于测试的中文语音。
Hello, welcome to the local speech-to-text system. This is a short English test recording.
```

### 3.4 离线验证

**执行命令**

```bash
LOCAL_FILES_ONLY=1 .venv/bin/python -m pytest -q -m real_model -o addopts=""
```

**输出**

```text
..                                                                       [100%]
2 passed, 19 deselected in 1.33s
```

### 3.5 最终测试结果

```text
python -m pytest -q
20 passed, 2 deselected

python -m pytest -q -m real_model -o addopts=""
2 passed, 20 deselected
```

### 3.6 服务启动冒烟测试

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```text
{"status":"ok"}
index_status=200
transcribe_status=200
{"text":"你好,欢迎使用本地语音识别系统,这是一段用于测试的中文语音。","language":"zh","duration_seconds":6.253,"processing_seconds":1.57}
```

---

## OpenCode 在各阶段承担的任务总结

| 阶段 | OpenCode 承担的工作 |
| --- | --- |
| 需求理解与技术设计 | 阅读需求、拆解功能、对比模型、制定架构与任务计划 |
| 功能开发与集成 | 生成前后端代码、测试脚本、模型下载脚本、音频样本 |
| 测试与问题修复 | 编写测试、定位 KeyError、处理网络下载失败、调整模型与提示词、验证离线运行 |

## 人工做出的关键决策

- 确认采用 faster-whisper 作为本地 ASR 方案
- 确认默认模型由 `base` 改为 `small`，以中文准确率为优先
- 确认使用 `initial_prompt` 而非额外依赖 OpenCC 来解决繁简问题
- 确认 F6 以“分片快照”方式实现近实时，而不是引入 WebSocket 复杂度

## 如何确认 AI 生成代码满足需求

1. 用 pytest 覆盖接口、音频校验、异常路径和模型调用
2. 用 `samples/` 下的真实音频执行真实模型测试
3. 用 uvicorn 真实启动服务并调用三个规定接口
4. 用 `LOCAL_FILES_ONLY=1` 验证离线运行
5. 对照需求文档第 9 节逐条检查完成标准

## 后续优化优先级

1. 将 F6 实时预览升级为 WebSocket 流式识别
2. 增加 VAD 静音检测，降低长音频重复推理
3. 提供模型热切换接口
4. 补充浏览器端自动化测试（Playwright）
