# 测试环境前端交接

本目录是 2026-11-03 测试环境当前前端文件的完整快照，用于后续界面优化。67 份原始文件、共 11,675,575 字节，均逐字节核对测试服务器 SHA-256；未在本次上传中改写页面、样式或交互算法。来源代码版本为 `58249c88a9e501b32dd8c2a9fb47b6a27206ae07`；该标识用于追溯项目内部测试版本。

## 从哪里开始

| 路径 | 用途 |
| --- | --- |
| `templates/` | 全部 25 份 Django HTML 模板，含当前页面和历史/备用页面 |
| `static/js/single_analysis.js` | 当前单图提交、轮询、状态恢复和 CSV 下载 |
| `static/js/batch_analysis.js` | 当前批量提交、SSE 进度及轮询降级 |
| `static/css/` | 样式及 `fonts/` 字体；部分样式仍内联在模板中 |
| `static/image/`、`static/img/` | Logo、背景和界面插图 |
| `static/mk/` | 页面相关使用手册 PDF，保留原文件名 |
| [页面与接口说明](docs/INTEGRATION.md) | 当前路由、请求字段、状态与兼容要求 |
| [路由参考](docs/routes-reference.json) | 从测试 URL 配置提取的路径、视图名及路由名 |
| [原始文件清单](source-manifest.json) | 每份原始文件的路径、字节数及 SHA-256 |

主要优化入口为 `templates/login.html`、`templates/register.html`、`templates/index.html`（单图）、`templates/analyse.html`（批量）以及对应 JS。`base.html` 供部分页面复用，但不少页面自带完整 HTML 和大量内联 CSS/JS，修改 base 不会自动影响所有页面。

文件名中的 `_test`、`_0412`、`_0414` 不代表当前测试服务正在使用它们。当前模板选择以路由、视图和 [入口表](docs/INTEGRATION.md) 为准；历史页面全部保留，便于比较。

## 如何联调

这是服务端渲染的 Django 前端，不是独立的 Vue/React/npm 项目。本目录不含运行后端，仓库原有 `code/` 是模型相关代码，也不是完整 Web 服务。直接双击 HTML、使用 Live Server 或 `python -m http.server` 都无法解析 `{% url %}`、`{% csrf_token %}`、模板变量和会话，不能据此判断业务功能是否正常。

建议工作方式：

1. 克隆仓库，建立自己的界面分支，例如 `git switch -c ui/layout-improvements`。
2. 获取项目负责人提供的开发/测试后端访问方式和测试账号；账号、密码通过私下渠道提供，不写入本仓库。
3. 将本目录内的 `templates/`、`static/` 作为后端项目同名目录的修改来源，保持相对路径。先在独立开发副本比对、集成，再启动已有的开发/测试后端；不要直接覆盖生产目录。
4. 使用后端提供的同源页面登录，访问 `/index/` 和 `/atest/` 联调。模型计算使用既有测试服务器；界面开发不需要在本机安装 GPU 模型环境。
5. 通过 Pull Request 交付修改，说明更改页面、兼容的 DOM/接口以及验证结果；由项目负责人按开发、测试、生产顺序集成。

从独立前端域名访问后端需要另行协调 Cookie、CSRF、跨域与代理配置；现有代码按同源会话工作。本交接不包含公开可用的测试账号、外网后端地址或自动部署配置。

## 修改时保留的约定

优先修改布局、排版、配色、响应式和文案。若调整 DOM ID、表单字段或按钮回调，需要同步检查相关 JS；不能仅因页面“看起来正常”就认为上传、进度和下载仍可用。关键约定见 [接口说明](docs/INTEGRATION.md)。

本次只交付前端原始文件与说明，不包含数据库配置、密钥、账号、模型权重、用户上传图片、分析结果、CSV 业务数据或日志。原有第三方库、字体、Logo 与手册保留其现有标识和权利归属；第三方依赖仍包含 CDN 引用，离线访问不保证全部样式可用。

## 已知基线情况

- 存在中英文切换、内联脚本、重复的 jQuery/样式依赖和历史页面，本次保留原状，以便界面人员在明确范围内优化。
- `static/css/ionicons.min.css` 引用的 `../fonts/ionicons.*` 在测试快照中不存在；当前主要页面也引用在线图标 CDN。不要把该资源缺失误认为上传遗漏。
- 检测计数与完整粒提取是不同阶段；当前完整粒分类含随机增强，完整粒数量可能变化。前端优化不应顺带改动模型、阈值或分类逻辑。
- 大批量任务可能排队数分钟。连接断开不代表服务器任务取消；保持现有 task_id、analysis_id、状态恢复和下载绑定。

## 文件完整性

`source-manifest.json` 只记录原始快照。验证脚本示例（在 `frontend/` 下执行，只用 Python 标准库）：

```python
import hashlib
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "source-manifest.json").read_text(encoding="utf-8"))
for item in manifest["files"]:
    data = (root / item["path"]).read_bytes()
    assert len(data) == item["bytes"]
    assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
print("67 original frontend files verified")
```

根目录 `.gitattributes` 为原始模板与静态资源关闭 Git 自动换行转换，保证克隆后的基线哈希可复核。后续开始优化后哈希变化是预期行为；用 Git 提交记录区分原始快照与界面改动，不要把修改后的文件伪记为原始基线。
