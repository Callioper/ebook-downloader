# 步骤 ⑥：渠道配置状态检查

## 步骤说明

读取 skill 根目录下的 `config.yaml`，打码展示各渠道配置状态。

**作用**：
- 管道启动时自动展示当前配置状态，用户可一眼确认各渠道是否就绪
- 所有敏感内容（API Key、Token、Webhook URL 中的密钥参数）在展示时自动打码
- 管道执行完毕后再次输出，以便确认执行过程中使用的最终配置参数

---

## 配置位置

```
ebook-downloader/
├── SKILL.md
├── config.yaml              ← 各步骤的 URL、Key、开关全部从这里读取
├── config.yaml.example      ← 模板，首次使用时复制为 config.yaml
├── scripts/config_reader.py ← 配置读取模块
└── ...
```

不再使用环境变量。各步骤直接通过 `ConfigReader` 的 getter 方法获取配置。

---

## 调用方式

```python
from scripts.config_reader import ConfigReader

cfg = ConfigReader()

# 获取各步骤配置
ebookdb_url = cfg.get_ebookdb_url()          # → http://127.0.0.1:10223
stacks_url  = cfg.get_download_manager_url() # → http://127.0.0.1:7788
stacks_key  = cfg.get_download_api_key()     # → "sk-cp-...f456"

# 显示打码后的渠道状态
print(cfg.show_channel_status())

# 检查最小可用配置
cfg.is_ready()   # → True/False
cfg.get_errors() # → ["download_manager.api_key 未配置"]
```

---

## 打码规则

| 字段类型 | 打码策略 | 示例 |
|----------|---------|------|
| API Key | 保留前 6 位 + 后 4 位 | `sk-cp-abc123def456` → `sk-cp-****f456` |
| Bot Token | 保留前 3 位 + 后 3 位 | `qqbot_secret_token_123456` → `qqb****456` |
| 代理 URL | 保留前 8 位 | `http://user:pass@proxy:8080` → `http://u****` |
| AppID | 不打码 | `102456789` → `102456789` |
| 端口/地址 | 不打码 | `http://127.0.0.1:10223` → `http://127.0.0.1:10223` |

---

## 输出格式示例

**未启用通知时：**

```
ebook-downloader 渠道配置状态
────────────────────────────────────────
  EbookDatabase: http://127.0.0.1:10223
  stacks 下载器: http://127.0.0.1:7788
  API Key:      sk-cp-****f456
  OCR 方案:     ocrmypdf+PaddleOCR
  通知渠道:     未启用
  代理:         未配置（直连）
────────────────────────────────────────
  状态: ✅ 最小配置可用
```

**启用 QQ Bot 通知时：**

```
ebook-downloader 渠道配置状态
────────────────────────────────────────
  EbookDatabase: http://127.0.0.1:10223
  stacks 下载器: http://127.0.0.1:7788
  API Key:      sk-cp-****f456
  OCR 方案:     MinerU
  MinerU WebUI: http://127.0.0.1:7860
  MinerU API:   http://127.0.0.1:8000
  通知渠道:     qqbot
    AppID:       102456789
    Token:       qqb****456
    频道 ID:     987654321
  代理:         未配置（直连）
────────────────────────────────────────
  状态: ✅ 最小配置可用
```

---

## 管道中的位置

```
[步骤 1-5 执行完成]
         │
         ▼
┌────────────────────────────────────────┐
│  步骤 ⑥：渠道配置状态检查               │  ← 新增
│  └─ 读取 config.yaml                   │
│  └─ 打码展示所有配置                    │
│  └─ 校验最小可用配置                    │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  步骤 ⑦：项目进度汇报（原步骤⑥）      │  ← 原步骤⑥ 后移
│  └─ 参照 report-template.md            │
│  └─ 推送到通知渠道                     │
└────────────────────────────────────────┘
```

---

## 注意事项

- `config_reader.py` 自动定位 skill 根目录。如果脚本被单独移动到别处，需手动传入 `config_path` 参数。
- 配置缺失不会抛异常，各 getter 返回 None/默认值，由调用方决定是否跳过对应步骤。
- 首次使用前，将 `config.yaml.example` 复制为 `config.yaml` 并填入实际值。
- `config.yaml` 已在 `.gitignore` 中，不会被提交到 git 仓库。
- 从环境变量迁移到 `config.yaml` 后，各步骤命令中不再出现 `$EBOOKDB_URL`、`$DOWNLOAD_MANAGER_URL` 等变量，改为 `python3 -c "from scripts.config_reader import ConfigReader; print(ConfigReader().get_ebookdb_url())"` 或直接在 Python 脚本中 import 使用。
