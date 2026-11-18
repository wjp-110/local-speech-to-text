# OpenCode 开发过程记录

## 阶段一：需求理解与技术设计

- 使用 OpenCode 阅读 `需求文档.md`，逐条提取 F1–F5 必做功能与 F6 加分功能。
- 明确技术约束：Python 3.12 + FastAPI、原生前端、本地开源 ASR、CPU 可运行、可离线。
- 通过方案对比，选择 `faster-whisper + CTranslate2 int8` 作为本地 ASR：
  - 对比过原版 whisper、Vosk、Web Speech API、云端 API 和 whisper.cpp。
  - 决策理由记录在 `docs/design.md`。
- 设计了“懒加载单例 + 依赖注入”的后端结构，使默认 pytest 可以用 Fake 服务替换真实模型，避免测试时下载权重。

## 阶段二：功能开发与集成

- 生成后端模块：`main.py`、`config.py`、`audio.py`、`asr.py`、`errors.py`、`schemas.py`。
- 生成前端页面：`static/index.html`、`styles.css`、`app.js`，实现录音、上传、状态显示、结果复制。
- 生成 `scripts/fetch_model.py`，把模型下载与在线/离线运行解耦。
- 生成 pytest 测试与 `pytest.ini`，默认跳过真实模型测试。

## 阶段三：测试与问题修复

1. **首次 Mock 测试失败**：`test_service_returns_joined_text_and_language` 报 `KeyError: 'device'`。
   - 原因：测试里用 `lambda` 替换 `WhisperModel`，没有真正实例化 Fake 类，构造函数参数没有被记录。
   - 修复：改为用工厂函数创建 `FakeWhisperModel` 实例并保存引用，再断言 `device` / `compute_type` / `language`。
   - 结果：`python -m pytest -q` 最终 20 passed。
2. **模型下载失败**：`scripts/fetch_model.py` 直连 HuggingFace 时报 `[Errno 54] Connection reset by peer`。
   - 处理：改用镜像 `HF_ENDPOINT=https://hf-mirror.com` 成功下载模型。
   - 文档已在 README 中说明首次联网下载、之后可离线运行。
3. **模型精度问题**：默认 `base` 模型把“语音识别”识别成“余音时别”。
   - 对比测试 `small` 模型后，中文文字正确，但输出繁体。
   - 修复：在 `language == "zh"` 时传入 `initial_prompt="请用简体中文转写普通话。"`，输出变为正确简体中文。
   - 最终决策：默认模型改为 `small`，`base` 作为低端机器的可选快速模式。
4. **离线验证**：设置 `LOCAL_FILES_ONLY=1` 后再次运行真实模型测试，2 passed，确认断网可用。
5. **异常处理补充**：`POST /api/transcribe` 增加兜底 `try/except`，确保非 `AppError` 的异常也转成带 `detail` 的 500 响应，前端能正常展示错误。

## OpenCode 在开发中承担的任务

- 需求拆解与方案设计
- 代码骨架生成与模块划分
- 自动化测试编写
- 文档撰写
- 错误定位与修复建议

## 自主做出的关键技术决策

- 模型：默认 faster-whisper `small` + int8 CPU（中文加简体提示词），低端机器可切换 `base`
- 上传限制：10 MB；录音上限：60 秒
- 测试隔离：用依赖注入 + marker 区分 Mock 与真实模型测试
- 前端录音格式：优先 WebM/Opus，兼容 OGG/WAV

## 如何确认 AI 生成代码满足业务需求

- 对照需求文档逐项检查功能点。
- 通过 pytest 覆盖接口、音频校验、语言参数和异常路径。
- 通过 `samples/` 下的真实音频运行真实模型测试，验证中英文均可识别。
- 检查统一启动命令与接口格式与需求文档一致。

## 后续优化优先级

1. 把实时预览从“分片快照”升级为 WebSocket 流式识别，降低延迟。
2. 增加 VAD 与静音跳过，提高长音频稳定性。
3. 提供模型热切换接口，无需重启服务。
4. 优化前端错误提示与无障碍支持。
