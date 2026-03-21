# 统一 Tab-Bar 组件和样式

## 问题分析
- `deliever_map.vue` 中直接实现了自定义 tab-bar
- `replenishment.vue` 使用了 `AppTabBar` 组件
- `AppTabBar` 组件存在方法名不一致（模板中使用 `navTo`，脚本中定义 `go`）和样式不统一的问题
- 需要统一所有页面的 tab-bar 样式，使用同一个组件

## 修改计划

### 1. 修改 `AppTabBar` 组件
- 修复方法名：将 `go` 方法改为 `navTo`
- 统一样式：使用与 `deliever_map.vue` 相同的样式类名和样式定义
- 处理激活状态：通过路径判断当前激活的 tab
- 确保链接使用 `pages.json` 中定义的路径

### 2. 修改 `deliever_map.vue`
- 移除直接实现的 tab-bar 代码
- 引入并使用 `AppTabBar` 组件
- 保留 `tab-bar-placeholder` 以保持布局一致

### 3. 修改 `replenishment.vue`
- 确保 `AppTabBar` 组件的使用方式正确
- 验证 `tab-bar-placeholder` 的使用

### 4. 检查其他页面
- 检查是否有其他页面使用了 tab-bar，确保它们也使用统一的组件

### 5. 验证修改
- 确保所有页面的 tab-bar 样式一致
- 确保所有链接都能正确导航到 `pages.json` 中定义的页面
- 确保激活状态的显示正确

## 技术实现要点
- 使用 `uni.getStorageSync` 或通过路径参数判断当前页面，以设置正确的激活状态
- 确保样式定义与 `deliever_map.vue` 中的一致
- 确保所有页面的布局结构一致，包括 `tab-bar-placeholder` 的使用