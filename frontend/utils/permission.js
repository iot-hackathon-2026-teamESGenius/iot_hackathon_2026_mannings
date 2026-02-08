/**
 * 页面访问权限：与 src/api/routers/auth.py 角色权限对应
 * - store_inventory: view_orders, view_inventory, submit_replenishment, view_alerts, view_forecast
 * - logistics: view_schedules, edit_schedules, view_routes, adjust_routes, view_alerts, handle_alerts, view_vehicle_tracking, export_reports
 * - admin: * 全部
 */
const PAGE_PERMISSIONS = {
  '/pages/index/index': ['view_alerts', 'view_forecast', 'view_schedules', 'view_routes', 'view_vehicle_tracking'],
  '/pages/index/stock': ['view_inventory', 'view_forecast'],
  '/pages/index/replenishment': ['submit_replenishment', 'view_inventory', 'edit_schedules', 'adjust_routes'],
  '/pages/index/deliver': ['view_schedules', 'view_routes', 'view_vehicle_tracking', 'edit_schedules', 'adjust_routes'],
  '/pages/index/operation': ['view_orders', 'view_alerts', 'handle_alerts'],
  '/pages/index/orders': ['view_orders'],
  '/pages/index/inventory': ['view_inventory'],
  '/pages/index/deliever_map': ['view_routes', 'view_vehicle_tracking'],
  '/pages/my': [] // 我的页面不校验权限，仅需登录
}

/**
 * 判断当前用户是否有权访问指定页面
 * @param {string} path - 页面路径，如 /pages/index/index
 * @param {{ permissions: string[] }|null} userInfo - 用户信息（含 permissions）
 * @returns {boolean}
 */
export function canAccessPage(path, userInfo) {
  if (!userInfo) return false
  const perms = userInfo.permissions || []
  if (perms.includes('*')) return true
  const required = PAGE_PERMISSIONS[path]
  if (!required || required.length === 0) return true
  return required.some(p => perms.includes(p))
}

const MENU_ITEMS = [
  { path: '/pages/index/index', title: '首页', extraIcon: { type: 'home-filled', color: '#0066CC' } },
  { path: '/pages/index/stock', title: '可售库存展望', extraIcon: { type: 'eye' } },
  { path: '/pages/index/replenishment', title: '补货计划', extraIcon: { type: 'cart' } },
  { path: '/pages/index/deliver', title: '车队调度', extraIcon: { type: 'location' } },
  { path: '/pages/index/operation', title: 'SLA 订单与预警', extraIcon: { type: 'info' } },
  { path: '/pages/my', title: '我的', extraIcon: { type: 'gear' } }
]

/**
 * 返回当前用户可见的菜单项（用于侧边栏）
 * @param {{ permissions: string[] }|null} userInfo
 * @returns {{ path: string, title: string, extraIcon: object }[]}
 */
export function getVisibleMenuItems(userInfo) {
  if (!userInfo) return [MENU_ITEMS[MENU_ITEMS.length - 1]] // 仅「我的」
  return MENU_ITEMS.filter(item => canAccessPage(item.path, userInfo))
}
