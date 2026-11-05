# 后端源码与前后端联调

这是 2026-11-05 从当前测试环境核对导出的后端源码，配合仓库已有的 [frontend/](../frontend/README.md) 使用。新增后端目录，不替换前端人员已经提交的页面优化，也不部署或重启服务器。

来源测试版本为 `58249c88a9e501b32dd8c2a9fb47b6a27206ae07`；它已包含单图原始输入保持、异步任务与批量数据库工作线程连接回收修正。源码与 2026-11-03 前端交接时的接口版本对应。

## 目录

| 路径 | 内容 |
| --- | --- |
| `spike/views.py` | 登录、单图/批量分析入口、进度、数据库页面与下载处理 |
| `spike/single_runtime.py` | 单图任务号、队列、状态、输入保持、提取与下载绑定 |
| `spike/batch_runtime.py` | 共用计算锁、检测模型缓存及结果路径/响应辅助 |
| `spike/db_runtime.py` | 线程池任务的数据库连接清理 |
| `spike/ulx_router.py` | 项目内多个 Ultralytics 版本的受控切换 |
| `spike/models.py`、`spike/migrations/` | 数据模型与现有迁移文件，不包含数据库数据 |
| `spike/management/commands/` | 已有数据导入命令；输入数据需单独提供 |
| `spike_test/urls.py` | 实际 Web 路由，与前端路由说明对应 |
| `spike_test/settings_base.py`、`settings_dev.py`、`settings_test.py` | 公开配置；测试数据库的敏感值通过环境变量提供 |
| `spike_test/settings_handoff.py` | 本次新增的本地联调配置，使用相邻 `frontend/` 和隔离 SQLite |
| `yolov8/`、`yolov8_current/`、`yolov10_current/` | 当前适配器与配套模型运行库源码、配置；不含权重 |
| `core/`、`processor/` | 已有历史处理辅助代码；部分旧 YOLOv5/7 路径依赖未随本次交接提供，当前三个模型主流程不走这些旧路径 |
| `requirements-dev.txt` | 已用 Python 3.11 开发环境验证的核心依赖列表；PyTorch 另配 |
| `requirements.txt` | 原环境依赖快照，不应视为任意平台的通用安装锁文件 |
| `source-manifest.json` | 538 份来源文件的原始/公开副本哈希及调整说明 |
| `third_party/ULTRALYTICS_AGPL-3.0.txt` | 随附 Ultralytics 代码的许可证文本；源文件原有声明保留 |

其中 536 份来源文件保持原始字节。两份公开配置仅移除内部主机提示或将数据库名称、用户名与允许主机改为环境变量，具体差异见清单。`settings_handoff.py` 等交接辅助文件为本次新增，不伪记为服务器原文件。

## 前后端如何对应

保持仓库布局：

```text
Spikelet-Cloud/
├── frontend/
│   ├── templates/
│   └── static/
├── backend/
│   ├── manage.py
│   ├── spike/
│   ├── spike_test/
│   └── yolov8/ ...
└── code/                  # 仓库原有的研究模型代码，保留
```

在 `backend/` 中显式选择 `spike_test.settings_handoff`。它让 Django 从 `../frontend/templates` 和 `../frontend/static` 读取当前界面，生成的分析文件放在忽略的 `backend/static/`，本地数据库放在 `backend/runtime/handoff/`。

前端接口、字段、任务状态和下载约定见 [联调接口说明](../frontend/docs/INTEGRATION.md)。当前后台主要使用 Django 会话 Cookie；提交后应持续查询任务至结束。`/index/` 为单图入口，`/atest/` 为批量入口。

## 本地检查与启动

使用项目负责人提供的现有 Python 环境，或单独建立 Python 3.11 虚拟环境并按其环境清单安装依赖。核心 Web 依赖及图像计算库见 `requirements-dev.txt`，其中不包含 torch/torchvision；这些需要另行配置为与目标机器兼容的版本。本次交接没有自动安装、下载或升级软件。

在仓库根目录打开 PowerShell，使用你准备好的 Python：

```powershell
cd backend
$env:YOLO_AUTOINSTALL = "false"
python manage.py check --settings=spike_test.settings_handoff
python manage.py migrate --settings=spike_test.settings_handoff
python manage.py runserver 127.0.0.1:8000 --settings=spike_test.settings_handoff
```

`migrate` 只会作用于该配置下新建的本地 SQLite 文件，不连接服务器数据库。没有迁移或导出生产/测试数据库的数据。原始 `manage.py`、ASGI、WSGI 的默认配置名仍为 `spike_test.settings`；本次没有公开真实的 settings.py，因此按上述命令显式选择 handoff 配置。使用 ASGI/WSGI 启动时也应由私有启动配置指定 `DJANGO_SETTINGS_MODULE`。

应用使用自定义的 `spike.models.User` 和 `Group`，运行 `createsuperuser` 不等于获得这个业务登录账号。空数据库没有已有角色和业务用户，登录/注册还需要负责人提供初始化方式或独立测试账号。不要将真实账号与密码提交仓库。

当只想查看模板、路由或修改样式时，不需要下载模型权重；现有项目在加载 URL/视图时仍会导入 torch 和图像依赖，不能把它当作只有 Django 一个依赖的静态预览程序。

## 实际图片推理还需要什么

公开源码不包含下列资源，请由项目负责人私下提供或继续使用已有测试服务器：

- `backend/weights/RGD-YOLO.pt`
- `backend/weights/yolov8m_raw.pt`
- `backend/weights/Yolov10m-raw.pt`
- `backend/eff_classify/training_datasets/model/classify.pth`
- 原版 `backend/eff_classify/training_datasets/for_cloud/` 类别目录和参考图片。现有分类器用 ImageFolder 从该目录建立类别映射，空目录或任意命名的类别目录不能替代原资源。
- 若使用表型/基因型数据库页面，还需单独准备相应数据和已有模型字段所需的数据库结构；本次只交付现有迁移，不自动补造历史数据。

模型标识仍为 `spike-yolo`、`yolov8`、`yolov10`。现有本机开发环境与服务器 GPU 环境不同；是否能查看登录页、系统检查通过，不等于已配置完整模型推理。请按开发、测试、生产流程联调，不将新仓库直接自动部署到现有生产目录。

## 可选 MySQL 测试配置

只有明确选择 `spike_test.settings_test` 时才使用 MySQL。公开副本要求从环境变量提供 `DJANGO_SECRET_KEY`、`DB_NAME`、`DB_USER`、`DB_PASSWORD`，主机默认为本机，允许主机可通过 `DJANGO_ALLOWED_HOSTS` 设置。请仅连接独立测试库；`.env.example` 只是变量清单，项目不会自动读取 .env 文件。

## 验证与后续修改

本次检查来源哈希、公开内容范围和 Python 语法，使用已有环境执行本地系统/回归检查；实际结果见 [交接检查记录](HANDOFF_CHECKS.md)。没有在本次上传过程中调用服务器模型、建立生产账号或写业务数据。

默认单进程内保存任务状态与锁。界面优化时保留 task_id、analysis_id、会话与下载对应关系；更换为多进程部署或新任务系统需单独设计和复测。批量长任务、单图满额 429、分类随机增强和阈值均保留当前行为。

模型运行库中的自定义层、数据配置和版本路由属于本项目实际依赖，不宜直接用最新 pip ultralytics 替换。独立的研究代码 `code/` 与此处按当前 Web 接口打包的运行库用途不同。
