# 科研界面主题 · 2026-11-04

本次为现有 Django 前端增加展示主题，不迁移框架。电脑端参考 GitHub Primer 的导航、操作区域与主要内容分区，单图页面采用左侧操作、右侧结果画布。视觉采用稻作与科研记录本的元素：霞鹜文楷艺术标题、米白纸纹、融入横幅的稻穗照片、自绘植物线稿和采样提示。工作区顶部移除了悬浮籽粒插画；登录、注册仍采用双栏品牌区域。机构 Logo 与署名保留。

## 修改入口

- `static/css/research-theme.css`：颜色、字体、布局、表单、表格、状态、响应式与轻动效。
- `static/js/research-ui.js`：展示文案的中英文同步、按钮按压反馈，以及批量页模型下拉框的展示增强。
- `static/image/grain-study.svg`：登录、注册使用的本地籽粒插画。
- `static/image/panicle-study.svg`：结果空状态的植物线稿；不代表实际分析结果。
- `static/image/a.webp`：原仓库已有的稻穗照片，作为横幅背景使用。
- `static/fonts/rgpas/`：本地网页字体、原始 OFL 许可证与来源说明。标题为霞鹜文楷的精简字库，正文搭配 Noto Sans SC 与 Manrope；本次新增 WOFF2 合计约 183 KiB。
- `tools/build_fonts.py`：可选字体构建工具；从官方仓库下载字体到本地缓存、按界面文字生成 WOFF2。增加中文标题或固定文案后可重新运行；字库未覆盖的动态字符使用系统字体回退。字体只随网页加载，不安装到 Windows。
- `templates/partials/research-brand.html`：登录、注册的品牌区域。
- `templates/partials/research-heading.html`：分析页标题、说明与照片横幅。
- `templates/partials/research-field-notes.html`：单图、批量页侧栏的图像准备提示。
- 登录、注册、单图、批量为重点页面；资源库、说明、个人信息及管理等当前模板接入公共主题。历史备用模板保持原状。

没有新增 React、动画框架或线上 CDN 依赖。按钮悬停、上传图标上浮、表单聚焦等反馈使用 CSS；按钮按下缩至 96.5%，释放时使用原生 Web Animations API 完成 420ms 的回弹。回弹逻辑只观察输入事件，不拦截或延迟点击、提交、导航与原有事件处理器；禁用控件不触发回弹。重复按压会取消上一次回弹，移出、失焦、取消触控都会清理按压状态。

批量页模型选择区域按内容收紧高度，电脑端宽度限制在 300px；移除工作区卡片统一最小高度造成的留白。下拉框采用圆角浅绿面板、柔和悬停与展开/收起过渡。原 `select#model` 继续作为提交与业务脚本读取的数据源，字段名和选项值不变；选择时同步触发原生 input/change 事件，并跟随原控件的禁用状态。支持方向键、Enter、空格、Home/End、Esc、Tab 和按名称查找选项。面板显示在独立浮层中，避免被卡片裁切，并在底部空间不足时向上展开。减少动态效果设置同样适用。

照片背景进入页面时做一次 18 秒的缓慢归位；空状态线稿有两次轻微浮动，随后静止。这些装饰不承担任务进度含义，实际分析状态仍由原有脚本控制。`prefers-reduced-motion: reduce` 下关闭新增动效，运行中切换此设置也会清理按钮动画。

本轮设计与浏览器验收以 1440px、1280px 电脑端为主。保留已有窄屏兼容规则，未新增手机版页面或流程；表格仍在自身容器中滚动。

## 本地预览

项目已安装预览依赖。双击根目录 `preview-frontend.cmd`，访问：

- `http://127.0.0.1:8765/` 登录
- `http://127.0.0.1:8765/register/` 注册
- `http://127.0.0.1:8765/index/` 单图分析
- `http://127.0.0.1:8765/atest/` 批量分析

通过上面的地址进入各页面。修改模板或 CSS 后刷新即可看到更新。关闭预览终端即可停止服务。页面不注入预览浮层或说明横幅。

重新安装时，使用项目环境执行 `python -m pip install -r frontend/requirements-preview.txt`。预览依赖按当前 Python 3.9 环境固定，仅用于本机回环地址的展示，不作为线上后端版本选择。

`tools/preview.py` 使用真正的 Django 模板渲染器解析模板、继承、路由与变量；上下文使用明确的预览用户名和空结果。预览不含数据库、认证或计算服务，POST 和业务 API 均返回“未连接业务后台”，不模拟成功结果。页面中的机构/资源和原版第三方 CDN 引用仍按原快照保留。

## 保留与验证

原有单图/批量传输脚本、模板内联 JS、关键 ID、输入字段、事件、表单提交地址、模板路由和 CSRF 标记均保持不变。模型、接口、阈值、队列、任务恢复和下载绑定不在本次修改范围。

已对 14 个修改模板的上述契约与原始 Git 基线逐项比较，两个业务传输脚本逐字节一致；15 个当前页面入口通过 Django 模板渲染检查，新增展示 JS 通过语法检查。电脑端检查覆盖主要布局、中英文显示、菜单收起、空状态与登录区域，并观察到按钮释放时的实际变换。字体资源通过本地 HTTP 正常加载，OFL 许可文件随字体交付。按压状态、重复操作、禁用、取消和减少动态效果使用事件测试补充验证。截图保存在项目 `.cache/frontend-qa/`。

这些检查不代表后端业务联调通过。真实登录、上传、排队、分析、进度恢复与下载仍需在测试后端按 `INTEGRATION.md` 验收。预览中也观察到原快照已有的脚本问题：部分导航初始化对空 `data-onclick` 调用 `includes`、资源库的语言函数操作缺失节点，以及单图页面 Popover 缺少 Popper 依赖。相关内联脚本及依赖引用已与原始基线核对，本次没有修改这些业务代码，不能据此宣称全站没有脚本错误。

部署时交付变更的 `templates/`、新增的 `templates/partials/`、CSS、展示脚本及 SVG，保留相对路径；`tools/preview.py` 和本地启动脚本不部署到生产。原始 `source-manifest.json` 保持不变，用于追溯收到的基线。

## 设计参考

- [GitHub Primer 布局](https://primer.style/product/getting-started/foundations/layout/)：导航、辅助操作与主要内容的分区关系。
- [霞鹜文楷](https://github.com/lxgw/LxgwWenKai)：艺术标题字体；精简后的内部字体名已重命名，原 OFL 许可保留。
- [Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc)、[Manrope](https://github.com/google/fonts/tree/main/ofl/manrope)：中文界面正文与英文排版。
- Apple 官网曾用于早期字号与动效参考；当前采用更丰富的稻作视觉，未使用 Apple 商标、图片或源代码。
- [Mobbin](https://mobbin.com/)：工作区、表单与状态的信息层级参考。
- [React Bits](https://reactbits.dev/)：轻量入场和微交互思路；未引入 React 组件。
- [Uiverse](https://uiverse.io/)：按钮、输入与悬停反馈参考；使用本地编写的样式。
- Page Flows 在本次访问中返回 403，未依赖其付费或不可访问内容。

参考用于设计思路，页面没有复制上述网站的收费素材或业务代码。
