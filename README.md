# PTE Coach · Read Aloud V1

用于个人日常训练的本地口语分析系统。可录音、转写、逐词对照、复听、测停顿与音高、查看可解释训练分、保存历史。**分数为未校准 0–100 Practice Score，不是 Pearson 分数，也不是通过概率。**

## 先看清楚本版边界

- 本地可运行：faster-whisper 独立 ASR、词时间戳、漏词／多词／替换／候选重复、Silero VAD、语速／停顿、pYIN 音高、逐词时长与能量、可解释内容／流利度训练分、规则 Coach、SQLite 历史。
- 可选：Azure 词／音素发音和韵律评分；WhisperX 精对齐；兼容 Chat Completions 的 LLM 补充建议。需要额外依赖、模型或本人配置的 API 凭据。
- 本地模式**不伪造 pronunciation/prosody 分数**。没有专用评测时显示“未评估”，仍显示原始声学指标。ASR 概率 ≠ 发音正确率，forced alignment ≠ GOP。
- 暂未实现：经英语学习者标注校准的本地 GOP、可靠 θ→s 检测、词／句重音正确性、音节边界、自我修正／重启检测、自动长期音素弱项挖掘、其他题型。相关字段与 provider/task_type 扩展位置已预留。
- “错序”以替换／插入／删除呈现，不额外声称能够识别语义上的移位。
- 单用户本机应用。不要直接暴露公网；未提供多人登录、跨设备同步或高并发隔离。

## Windows 快速启动（推荐先用 CPU）

本仓库是源代码版本。完整的本机模型和已安装依赖在桌面的 `PTE-Coach-Local-2026-09-16.zip` 中；从 GitHub 新克隆后，需要按下面步骤安装 Python、FFmpeg、依赖并准备模型，或从该 ZIP 复制 `models` 和 `.venv`。

安装 Python **3.12** 和 FFmpeg，并确保 `ffmpeg -version` 可运行。解压项目，在项目目录打开 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/doctor.py
.\.venv\Scripts\python.exe scripts/download_model.py
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
```

浏览器打开 `http://127.0.0.1:8765`。输入原文 → 开始录音 → 结束 → 试听 → 分析。首次下载 ASR 需要访问 Hugging Face。麦克风权限需要允许；用实际出声的录音，不要默念。手机访问另一台电脑的 HTTP 地址通常无法使用麦克风；本版按同一台电脑使用设计。

Linux/macOS：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_model.py
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
```

不要使用多 `--workers`；本版只有一个模型工作线程，防止重复加载显存与 SQLite 启动恢复冲突。CPU 首次 pYIN/JIT 初始化会慢一些。

## 你的 RTX 5060 怎么用

默认 `cpu + int8 + small.en`，先确认完整流程。没有在你的显卡上实测，不能保证某一 CUDA 组合可用。

安装与当前 CTranslate2 匹配的 NVIDIA CUDA/cuDNN 运行库后，在同一个终端设置：

```powershell
$env:PTE_DEVICE='cuda'
$env:PTE_COMPUTE_TYPE='float16'
$env:PTE_ASR_MODEL='small.en'
```

再启动服务。失败时改回 CPU；程序不会默默把模型故障替换成假结果。模型路径也可以填写已下载的本地 CTranslate2 模型目录。升级 `medium.en` 或其他模型后分开比较历史，避免把模型变化误当进步。GPU 安装以 [faster-whisper 文档](https://github.com/SYSTRAN/faster-whisper) 为准。

## 开启词／音素发音评测（可选，云端）

只有你显式设置 `PTE_ALLOW_CLOUD=true` 才会发送数据。Azure 会收到 WAV 音频和原文，可能产生服务费用；项目不包含密钥，也不会替你创建账户。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
$env:PTE_ALLOW_CLOUD='true'
$env:PTE_PRONUNCIATION='azure'
$env:AZURE_SPEECH_KEY='你自己的密钥'
$env:AZURE_SPEECH_REGION='你的资源区域'
```

重启服务。使用 en-US、连续识别和 phoneme granularity；返回的音素、音节和原始 provider evidence 可逐词查看。连续模式不启用 EnableMiscue，内容差异仍由独立 ASR 比较。跨段准确度采用词分算术平均，韵律分按每段词数加权：这是本项目明确声明的聚合，不冒充厂商 overall 或 Pearson。此适配器已实现，但本次没有真实 Azure 凭据，未完成云端实测。

## 可选 WhisperX

建议在独立虚拟环境安装 `whisperx`，确认其依赖与本项目相容后，设置 `PTE_ALIGNMENT=whisperx`。首次需要下载英语对齐模型。对齐对象是 ASR 转写文本，而不是把原文硬塞进音频；避免掩盖漏词。安装失败时可用默认 ASR 词边界。精对齐失败会明确提示退回估计边界。此可选路径未在本次环境验证。

## 可选 LLM Coach

设置 `PTE_ALLOW_CLOUD=true`、`PTE_LLM_BASE_URL`、`PTE_LLM_API_KEY`、`PTE_LLM_MODEL`。URL 为 API 前缀，程序追加 `/chat/completions`。接口需支持 JSON object response format。只发送规则 Coach 已选中的少量证据和建议，不发送音频或密钥到模型上下文；最多补充三条建议，不能修改分数。请求失败自动保留规则教练。支持 provider 的结果格式，不保证所有“兼容 API”实现完全一致。

`.env.example` 只是配置说明；程序不会自动加载 `.env`，请使用终端环境变量。默认不启用任何云端功能。

## 数据与可解释性

数据位于 `data/` 或 `PTE_DATA_DIR`：`history.sqlite3`、每次原始音频和规范化 WAV。停止服务后备份整个目录，包含数据库和音频。每次训练可以导出 JSON；删除记录会删除对应音频。数据没有自动上传或加密，使用操作系统账户保护。

展开“为什么得到这个分数”可查看原始值、扣分项和公式；完整规则在 `app/analysis/rubric.json`。当前阈值是公开的工程启发式，**尚未经 PTE 标注校准**。修改规则应提高版本；系统另存规则哈希。未评估维度不算零分，总分按实际覆盖权重重新归一化，因此覆盖不同的总分不可直接比较。

WPM 用首个语音开始到最后语音结束为分母；articulation rate 用 VAD 语音时长。首尾静音不算句内停顿。≥200/500/1000ms 是累积计数，不是互斥桶。停顿来自 VAD；候选异常来自无标点处 ≥500ms 词间隔，两者不保证一致。音节率由字典／拼写估算，重音并未完成声学正确性判断。

历史页提供最近 1000 条原始 WPM 趋势数据，图中展示最近 30 次；列表展示最近 200 条。数据库不因此删除更早记录。下一阶段可添加分页和题目难度分层。

## 开发与测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm run check
```

测试注入的 ASR 只存在于 `tests/`，不是生产 fallback。合成正弦用于验证音高测量，不证明发音评分准确。实际公共语音 smoke 结果见 `docs/smoke-result.json`。详细状态见 `docs/validation.md`。

模块说明、方案取舍和后续实验门槛见 `docs/design.md`；实现步骤见 `docs/implementation-plan.md`。没有训练新模型。

## 下一阶段如何做得可靠

1. 录制你自己的不同长度 RA，逐词人工核对 ASR、边界和候选停顿；先解决误报。
2. 对比 WhisperX、不同 ASR 与专用评测结果，测词边界误差、重复保留率、发音低分误报率；不要只看整句转写准确率。
3. 收集经过许可且有教师音素／流利度评分的数据，划分开发集和独立留出集，做 GOP/phone posterior 校准、置信度拒判和口音公平性检查，再让本地音素分进入总分。
4. 扩展 RS 等题型，保持独立的任务评分器、题目难度与历史比较签名。
