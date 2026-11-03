# 页面入口与前后端约定

本说明基于 2026-11-03 测试版本的实际 URL 配置、模板与前端交互代码。JSON 路由全表见 [routes-reference.json](routes-reference.json)。这里只提取联调所需信息，未公开服务器配置或后端业务实现。

## 当前页面入口

| 路径 | 模板 | 说明 |
| --- | --- | --- |
| `/` | `login.html` | 登录；POST 后端成功时重定向到首页 |
| `/register/` | `register.html` | 注册页面 |
| `/index/` | `index.html` | 当前单图分析页面 |
| `/atest/` | `analyse.html` | 当前批量分析页面 |
| `/adatabase/` | `database.html` | 数据库浏览 |
| `/adatabase2/<image_name>/` | `database2.html` | 数据库详情 |
| `/use/` | `use.html` | 使用说明 |
| `/user_single/` | `dex.html` | 个人信息页 |
| `/user_show/` | `user_show.html` | 用户管理相关页面 |
| `/user_add/` | `user_add.html` | 用户添加相关页面 |
| `/user_show/<nid>/edit/` | `user_edit.html` | 用户编辑相关页面 |
| `/sort/` | `sort.html` | 当前保留的分类相关页面 |
| `/upload/` | `upload.html` | 当前保留的上传入口 |
| `/entity/` | `entity.html` | 当前保留的展示入口 |
| `/try/?nid=...` | `try.html` | 用户相关检测/性状数据展示 |

模板都保留不等于各入口都做过相同程度的业务验证。单图/批量主流程是此次交接的重点；管理员入口还受既有会话和角色逻辑影响，不应在 UI 中将其等同于普通用户入口。

## 登录与公共表单

- 当前页面主要依赖 Django 会话 Cookie。请求继续使用同源凭据，不要把模型接口改为匿名请求或把会话信息放进 URL。
- 登录 POST `/` 的字段为 `email`、`password`、`login_type`。现有普通用户登录类型为 `user`；保留现有用户/管理员选项与后端配合。
- 注册后端读取 `username`、`password`、`email`；现有模板和内联 JS 共同完成字段收集，不宜只根据 input 的显示名称修改字段。
- 保留 `{% csrf_token %}` 和当前 JS 的 `X-CSRFToken` 传递。保留模板中的 `{% url %}`、变量及循环，实际 URL 由后端渲染。
- `/logout/` 为当前退出入口；`/forget/` 为现有找回相关请求入口。不要在界面优化中自行改变认证或找回流程。

## 单图完整流程

代码入口：`templates/index.html` + `static/js/single_analysis.js`。

| 操作 | 方法与路径 | 字段/含义 |
| --- | --- | --- |
| 提交计数 | POST `/test/`，multipart/form-data | `file` 为原图；`model` 为模型标识；`task_id` 为独立任务号 |
| 查询计数 | GET `/test/?task_id=...` | 使用同一会话、同一 task_id |
| 提交完整粒提取及性状分析 | POST `/complety/`，multipart/form-data | `analysis_id`、`model`、`file`（已计数文件名字符串）及本次提取 `task_id`；此处不是重新上传原图 |
| 查询提取 | GET `/complety/?task_id=...&analysis_id=...` | 与计数结果绑定 |
| 下载单图性状 | GET `/downloadSingle/?analysis_id=...` | CSV 文件流，与当前分析绑定 |

模型取值保留 `spike-yolo`（界面 RGD-YOLO）、`yolov8`、`yolov10`。

异步响应中，202 表示已接收/仍在处理，不能直接显示“完成”；以 JSON 的 `done` 和 `status` 判断。公共状态字段包括 `task_id`、`kind`、`status`、`phase`、`done`、`error`、`progress`。状态可能为 `queued`、`running`、`finished`、`failed`。

计数完成结果包含 `analysis_id`、`filename`、`model`、`image_number`、`original_url`、`result_url`；`image_number` 在现有实现中可能是数字字符串，前端会转换。提取完成包含 `sum`、`image_names`、`complete_urls` 及匹配的 `analysis_id`。使用服务器返回的 URL，不从原文件名猜测静态路径。

常见状态：401 登录失效、404 任务不存在/不属于当前会话/过期、409 冲突、429 单图任务位已满。当前单进程单图排队加运行任务位为 4；拒绝要清晰提示，不能无限自动重提。网络中断不证明后端停止。

与现有脚本耦合的 DOM 至少包括 `options-form`、`form1`、`birthday`、`file`、`model`、`btn`、`button1`、`summary`、`sort`、`completey`。两份提交表单通过 `data-single-count-url`、`data-single-extract-url` 提供后端地址；本表不是所有 DOM 依赖的穷尽列表，重构前应检查脚本的全部选择器。

现有 JS 用 sessionStorage 保存待处理任务和分析上下文，用 localStorage 的 `language` 控制语言。保留恢复查询及“更换图片/模型后清理旧结果”的行为，避免将上一次结果展示为新图片结果。

## 批量完整流程

代码入口：`templates/analyse.html` + `static/js/batch_analysis.js`。

| 操作 | 方法与路径 | 字段/含义 |
| --- | --- | --- |
| 提交批量 | POST `/analyse/`，multipart/form-data | `task_id`、`model`，重复的 `file` 字段携带多张原图 |
| 状态快照 | GET `/analyse/status/?task_id=...` | 当前会话下该任务的状态 |
| SSE 进度 | GET `/analyse/progress/?task_id=...` | EventSource；连接失败时现有脚本降级到状态轮询 |
| 下载批量结果 | GET `/download/` | ZIP 文件流，绑定当前会话保存的批量结果；不是 JSON |

模板的 `window.RGPAS_BATCH` 提供 `analyseUrl`、`progressUrl`、`statusUrl`；保留 Django 路由解析。界面选框可能名为 `YOLO`，实际发送给后端的字段仍为 `model`。

批量 POST 是长请求，处理过程中前端通过 SSE/轮询展示进度。状态包含 `task_id`、`status`、`phase`、`current_file`、`index`、`total`、`progress`、`results`、`done`、`error`。一张图的结果行含 `name`、`filename`、`number`、`complete_count`、`original_url`、`result_url`、`complete_urls`。保留逐行任务对应和新批次开始时清空旧结果的逻辑。

保留上传时禁用重复提交的行为；POST 断线时继续查询已提交任务，不要立即再次上传。同一个会话的第二个批量可能被拒绝；本系统没有通用的“关闭浏览器即可取消任务”语义。批量 ZIP 使用当前会话结果，若需要在多个批次间任意选择历史下载，需要先与后端共同设计，不能仅增加前端 task_id 参数便假定已有支持。

## 界面优化后的最低验收

1. 登录与退出，中英文切换，桌面与窄屏布局。
2. 单图三个模型：上传原图、计数、完整粒提取、性状 CSV；更换图片/模型后不显示旧结果。
3. 3–5 张批量：进度结束、逐图名称/计数/结果图一致；ZIP 可解压，图片与 CSV 对应本批次。
4. 排队、登录失效、接口报错、断网后的提示与恢复查询；下载不能变成保存 HTML 错误页。
5. 需要压测或大批量 GPU 联调时提前预约测试窗口。界面视觉检查和普通页面请求不能替代实际计算容量测试。

本说明不授权修改模型算法、阈值、认证后端或生产部署；涉及接口/流程的改动应与项目负责人共同确定范围。
