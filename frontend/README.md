# 万宁门店自提 SLA 优化 - 前端

Vue3 (选项式) + uni-app + uni-ui，对接后端 FastAPI REST API（`http://localhost:8000/api`）。

---

## 技术栈

| 项 | 说明 |
|----|------|
| 框架 | Vue 3 (Options API) + uni-app |
| UI | uni-ui、uni-icons |
| 图表 | qiun-data-charts (uCharts) |
| 地图 | uni-map-common |
| 样式 | SCSS |
| 请求 | `utils/api.js`：`apiGet` / `apiPost` / `apiPut`，Base URL: `http://localhost:8000/api`；`getToken` / `setToken` 存读 Token；`getUserInfo` / `setUserInfo` 存读当前用户（含 permissions、store_ids）；`getSelectedStore` / `setSelectedStore` 存读当前选中门店；请求自动带 `Authorization: Bearer` |
| 权限 | `utils/permission.js`：`canAccessPage(path, userInfo)`、`getVisibleMenuItems(userInfo)`，与后端 `src/api/routers/auth.py` 角色权限对应 |

---

## 角色权限与门店选择

- **角色**（见后端 `auth.py`）：`store_inventory`（门店库存）、`logistics`（物流）、`admin`（全部）。无权限的页面进入时会提示并跳回首页。
- **门店**：`store_ids` 为 `None` 表示可访问所有门店；否则仅可访问指定门店。首页导航栏中间为**当前门店**，点击可下拉选择有权限的门店；选中后保存到本地，首页及 SLA 订单/预警等接口会按 `store_id` 筛选数据。

---

## 页面与接口对应

| 页面 | 路径 | 使用的 API | 说明 |
|------|------|------------|------|
| 首页 | `pages/index/index` | `GET /dashboard/kpi`、`GET /dashboard/trend`、`GET /dashboard/alerts-summary` | KPI 卡片、SLA 趋势图、实时预警 |
| 需求预测 | `pages/index/forcast` | `GET /forecast/demand` | 需求预测图表与列表 |
| 补货计划 | `pages/index/replenishment` | `GET /planning/replenishment` | 补货计划列表与状态（按权限可见） |
| 车队调度 | `pages/index/deliever_map` | `GET /planning/schedules`、`GET /planning/routes/map-data`、`GET /planning/vehicles/realtime` | 车队调度地图、车辆列表、路线规划 |
| 登录 | `pages/login` | `POST /auth/login` | 用户名密码登录，成功后 `setToken`、`setUserInfo`，可跳转首页 |
| 我的 | `pages/my` | `GET /auth/validate`、`POST /auth/logout` | 校验 Token 显示用户信息，登出清除 Token/用户/选中门店 |
| 门店列表 | — | `GET /auth/stores`（需登录） | 当前用户可访问的门店列表，用于首页门店下拉 |

---

## 本地运行

1. **后端**：在项目根目录启动 FastAPI（端口 8000）  测试环境：windows 11
    
   ```bash
   source venv/bin/activate  # Windows: venv\Scripts\activate

   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **前端**：在 HBuilderX 中打开 `frontend`，运行到浏览器 / 小程序模拟器。  
   - H5 访问时，前端请求 `http://localhost:8000/api`，需保证后端已启动且 CORS 已配置。
   - [查看接口文档](http://localhost:8000/api/docs)
---

## 目录结构

```
frontend/
├── README.md           # 本说明（修改页面时请同步更新）
├── App.vue
├── main.js
├── pages.json          # 路由与 tabBar
├── utils/
│   ├── api.js          # 统一 API：apiGet / apiPost / apiPut；getToken / setToken；getUserInfo / setUserInfo；getSelectedStore / setSelectedStore
│   └── permission.js   # 页面权限：canAccessPage、getVisibleMenuItems，与后端角色对应
├── pages/
│   ├── index/
│   │   ├── index.vue   # 首页
│   │   ├── forcast.vue  # 需求预测
│   │   ├── replenishment.vue # 补货计划
│   │   └── deliever_map.vue  # 车队调度地图
│   ├── login.vue       # 登录
│   └── my.vue          # 我的
└── components/
    ├── app-nav-bar.vue # 与首页一致的固定顶栏（返回/菜单 + 标题 + 我的）
    └── app-tab-bar.vue # 统一底部导航栏（首页、需求预测、补货、调度、我的）
```

---

## 品牌与视觉规范（与项目根 README 一致）

| 项 | 值 |
|----|-----|
| 主色调 | `#0066CC`（万宁品牌蓝） |
| 一级标题 | 36rpx（约 18px） |
| 正文 | 26–28rpx（约 14px） |
| 风险等级 | 低 `#0066CC`、中 `#FFC107`、高 `#FD7E14`、严重 `#DC3545` |

卡片与区块：内容区 `padding: 24rpx`，卡片 `padding: 28rpx 24rpx`、`margin-bottom: 24rpx`，统计行 `padding: 20rpx 24rpx`、`margin-bottom: 24rpx`。

---

## 清单检查（与待完成任务.docx 对照）

当前前端已实现内容（可与 docx 清单逐项核对是否有遗漏）：

- [√] 首页：KPI 卡片、SLA 趋势图、实时预警、快捷入口；侧栏跳转需求预测、补货计划、车队调度、我的
- [√] 需求预测：`GET /forecast/demand`，需求预测图表与列表，支持按门店和 SKU 筛选
- [√] 补货计划：`GET /planning/replenishment`，补货计划列表与状态，支持调整和审批
- [√] 车队调度：`GET /planning/schedules`、`GET /planning/routes/map-data`、`GET /planning/vehicles/realtime`，车队调度地图、车辆列表、路线规划
- [√] 登录：`POST /auth/login`，Token 存储与跳转
- [√] 我的：`GET /auth/validate`、`POST /auth/logout`，用户信息与退出
- [√] 品牌色 `#0066CC` 与风险等级色、统一边距（见「品牌与视觉规范」）
- [√] 统一底部导航栏：所有页面使用统一的 `app-tab-bar.vue` 组件，样式一致

若 docx 中还有未实现项，请将条目贴出或导出为文本后补充实现，并同步更新本 README。

---

## 修改页面时请同步更新本 README

- 新增/删除页面：更新「页面与接口对应」表及「目录结构」。
- 新增/更换接口：更新对应页面的「使用的 API」列。
- 品牌/间距调整：在「品牌与视觉规范」或「变更记录」中说明。

---

## 变更记录

- **初始版本**：新增 `frontend/README.md`，约定「修改页面须同步更新本 README」。
- **首页**：对接 `GET /dashboard/kpi`、`/dashboard/trend`、`/dashboard/alerts-summary`；侧栏抽屉增加跳转：需求预测、补货计划、车队调度、我的。
- **需求预测**（`pages/index/forcast.vue`）：对接 `GET /forecast/demand`，需求预测图表与列表，支持按门店和 SKU 筛选。
- **补货计划**（`pages/index/replenishment.vue`）：对接 `GET /planning/replenishment`，补货计划列表与状态，支持调整和审批。
- **车队调度**（`pages/index/deliever_map.vue`）：对接 `GET /planning/schedules`、`GET /planning/routes/map-data`、`GET /planning/vehicles/realtime`，车队调度地图、车辆列表、路线规划。
- **登录**（`pages/login.vue`）：对接 `POST /auth/login`，成功后 `setToken`、`setUserInfo` 并跳转首页。
- **我的**（`pages/my.vue`）：对接 `GET /auth/validate`、`POST /auth/logout`，展示用户信息与退出登录。
- **utils/api.js**：`getToken` / `setToken`；`getUserInfo` / `setUserInfo`；`getSelectedStore` / `setSelectedStore`；登出时清除用户与选中门店。最近新增 `apiPut`（PUT 请求封装），供前端提交调度调整等接口使用。
- **角色权限与门店**：`utils/permission.js` 按后端角色控制侧栏菜单与页面进入；首页导航栏支持点击下拉选择当前门店（`GET /auth/stores`），选中门店持久化后，首页及其他接口会按 `store_id` 筛选数据。
- **布局与顶栏统一**：使用 `components/app-nav-bar.vue`（与首页一致的固定顶栏）、`components/app-tab-bar.vue`（统一底部导航栏）；所有页面统一：顶栏固定、内容区 `padding: 0 30rpx`、底部预留 tabBar 高度（`tab-bar-placeholder`）。
- **品牌与边距统一**：主色改为万宁蓝 `#0066CC`（导航、按钮、Tab、图表、状态标签）；风险等级按规范：低 `#0066CC`、中 `#FFC107`、高 `#FD7E14`、严重 `#DC3545`；各页内容区 24rpx、卡片 28rpx 24rpx、卡片间距 24rpx、统计行 20rpx 24rpx，首页 KPI 网格 gap 16rpx。
- **统一底部导航栏**：修改 `components/app-tab-bar.vue` 组件，统一所有页面的底部导航栏样式。
- **导航功能修复**：修复了首页导航栏右侧用户图标点击不跳转的问题，以及 `app-tab-bar.vue` 组件点击不跳转的问题。

---

## 如何在本地运行项目

### 1. 环境要求
- Node.js 14.0 或以上
- HBuilderX 3.0 或以上
- Python 3.7 或以上（用于运行后端服务）

### 2. 运行后端服务
```bash
cd f:\fly\Hackathon\iot_hackathon_2026_mannings

# 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行后端服务
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 运行前端项目
1. 打开 HBuilderX
2. 点击 "文件" -> "打开目录"
3. 选择 `iot_hackathon_2026_mannings\frontend` 目录
4. 等待项目加载完成
5. 点击工具栏中的 "运行" 按钮
6. 选择运行方式（如 "运行到内置浏览器（app）" 或 "运行到小程序模拟器"）


### 6. 测试账号
- 用户名：`admin`
- 密码：`admin123`

---

## 注意事项

1. **API 地址配置**：前端默认 API 地址为 `http://localhost:8000/api`，如果后端服务运行在不同的地址或端口，请修改 `utils/api.js` 文件中的 `baseURL`。

2. **跨域问题**：如果遇到跨域问题，请确保后端服务已配置 CORS。后端代码中应包含类似以下配置：
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **地图组件**：车队调度页面使用了 uni-app 的地图组件，需要在 `manifest.json` 中配置地图 API 密钥。当前已配置高德地图密钥。

4. **权限控制**：前端实现了基于角色的权限控制，如果遇到权限问题，请检查后端返回的用户角色是否正确。

5. **数据持久化**：前端使用 `uni.setStorageSync` 和 `uni.getStorageSync` 进行数据持久化，包括 Token、用户信息和选中的门店。

6. **错误处理**：前端实现了基本的错误处理，如果遇到 API 调用失败，请检查浏览器控制台中的错误信息。
