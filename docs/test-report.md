# 测试报告

> 本文记录自动化测试与真实模型验证结果。具体数值在测试执行后补充。

## 1. 测试环境

| 项目 | 值 |
| --- | --- |
| 操作系统 | macOS（开发）/ Windows 11 x64（目标复现环境） |
| Python | 3.11（开发）/ 3.12（目标） |
| 模型 | faster-whisper `small`（默认），CPU int8 |
| 浏览器 | Chrome / Edge 最新稳定版 |

## 2. 自动化测试

执行命令：

```bash
python -m pytest -q
```

结果：**20 passed, 2 deselected**（`python -m pytest -q`，Mock 测试不下载模型）

覆盖用例：

- 健康检查：`GET /health`
- 正常识别：中文 / 英文
- 非法参数：非法 language、缺少 file
- 音频处理：空文件、损坏文件、正常 WAV
- 文件格式：不支持扩展名返回 415
- 文件大小：超过 10 MB 返回 413
- 模型异常：Mock 模型失败返回 500
- 模型集成：Mock `WhisperModel` 验证语言参数与结果拼接
- 前端页面：首页包含录音控件

## 3. 真实模型测试

执行命令：

```bash
python -m pytest -q -m real_model -o addopts=""
```

| 样本 | 语言 | 参考文本关键词 | 实际输出（默认 `small` + 简体提示词） | 结果 |
| --- | --- | --- | --- | --- |
| `samples/chinese.wav` | zh | 欢迎 | 你好,欢迎使用本地语音识别系统,这是一段用于测试的中文语音。 | 通过（与参考文本一致） |
| `samples/english.wav` | en | welcome | Hello, welcome to the local speech-to-text system. This is a short English test recording. | 通过（与参考文本一致） |

`small` 模型实测处理耗时：中文 1.531s，英文 1.213s；音频时长分别为 6.253s / 6.647s。

对比测试：`base` 模型速度更快（0.612s / 0.473s），但中文输出出现“余音时别系统”等错字；因此默认改为 `small`，并通过 `initial_prompt` 保证输出简体中文。低端机器仍可用 `ASR_MODEL_SIZE=base` 切换到快速模式。

另已完成 uvicorn 真实启动冒烟测试：

- `GET /health` → `{"status":"ok"}`
- `GET /` → HTTP 200
- `POST /api/transcribe` 上传 `samples/chinese.wav` → HTTP 200，文本“你好,欢迎使用本地语音识别系统,这是一段用于测试的中文语音。”

## 4. 手动验证清单

| 场景 | 状态 | 说明 |
| --- | --- | --- |
| 浏览器麦克风录制中文并识别 | 需用户手动验证 | 本环境无真实麦克风与浏览器交互；启动后选择 zh 录音即可 |
| 浏览器麦克风录制英文并识别 | 需用户手动验证 | 同上，选择 en |
| 上传中文 WAV 文件并识别 | 已通过 | 通过 `TestClient` 以 multipart 提交 `samples/chinese.wav` |
| 上传英文 WAV 文件并识别 | 已通过 | 通过 `TestClient` 以 multipart 提交 `samples/english.wav` |
| 麦克风权限被拒绝时的表现 | 需用户手动验证 | 代码已处理 `NotAllowedError`，浏览器拒绝权限时应显示提示 |
| 无外网情况下完成识别 | 已通过 | `LOCAL_FILES_ONLY=1` 下真实模型测试 2 passed |

## 5. 已知问题

1. 默认 `small` 模型在普通 CPU 上单段 6 秒音频约需 1.2–1.5 秒；低端机器可设 `ASR_MODEL_SIZE=base`。
2. 实时预览采用“累积音频快照”方式，越到后面重复推理越多；分片边界处可能截断词语，最终结果以停止后的完整识别为准。
3. 中文简体输出依赖 `initial_prompt`，对极端口音或非普通话场景不保证完全简体。
4. 未实现中英文自动检测（属于加分项），需用户手动选择语言。
5. 本自动化环境无真实麦克风，浏览器麦克风交互需按 README 在本机手动验证一次。
