// 简单的 REST API 请求封装，统一管理后端地址
// Base URL 指向 FastAPI 服务的 /api 前缀
const API_BASE_URL = 'http://localhost:8000/api'
const TOKEN_KEY = 'mannings_token'
const USER_INFO_KEY = 'mannings_user_info'
const SELECTED_STORE_KEY = 'mannings_selected_store'

/** 读取本地 Token（登录后由 login 页面写入） */
export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

/** 写入/清除 Token（登录成功写入，登出清除） */
export function setToken(token) {
  if (token) {
    uni.setStorageSync(TOKEN_KEY, token)
  } else {
    uni.removeStorageSync(TOKEN_KEY)
    uni.removeStorageSync(USER_INFO_KEY)
    uni.removeStorageSync(SELECTED_STORE_KEY)
  }
}

/** 读取当前用户信息（含 permissions、store_ids），登录后写入；若仅有 Token 可配合 validate 恢复 */
export function getUserInfo() {
  try {
    const raw = uni.getStorageSync(USER_INFO_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

/** 写入用户信息（登录成功时调用） */
export function setUserInfo(info) {
  if (info) {
    uni.setStorageSync(USER_INFO_KEY, JSON.stringify(info))
  } else {
    uni.removeStorageSync(USER_INFO_KEY)
  }
}

/** 读取当前选中的门店 { store_id, store_name } */
export function getSelectedStore() {
  try {
    const raw = uni.getStorageSync(SELECTED_STORE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

/** 保存当前选中的门店 */
export function setSelectedStore(storeId, storeName) {
  if (storeId && storeName) {
    uni.setStorageSync(SELECTED_STORE_KEY, JSON.stringify({ store_id: storeId, store_name: storeName }))
  } else {
    uni.removeStorageSync(SELECTED_STORE_KEY)
  }
}

function _headers(extra = {}) {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra
  }
}

/**
 * GET 请求封装
 * @param {string} path - 例如 '/dashboard/kpi'
 * @param {Object} options - 可选参数 { params, header }
 * @returns {Promise<any>} - 解析后的响应数据 (res.data)
 */
export function apiGet(path, options = {}) {
  const { params = {}, header = {} } = options

  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE_URL + path,
      method: 'GET',
      data: params,
      header: { ..._headers(), ...header },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

/**
 * POST 请求封装
 * @param {string} path - 例如 '/planning/routes/optimize'
 * @param {Object} data - 请求体
 * @param {Object} options - 可选参数 { header }
 * @returns {Promise<any>} - 解析后的响应数据 (res.data)
 */
export function apiPost(path, data = {}, options = {}) {
  const { header = {} } = options

  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE_URL + path,
      method: 'POST',
      data,
      header: { ..._headers(), ...header },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

/**
 * PUT 请求封装
 * @param {string} path
 * @param {Object} data
 * @param {Object} options
 * @returns {Promise<any>}
 */
export function apiPut(path, data = {}, options = {}) {
  const { header = {} } = options

  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE_URL + path,
      method: 'PUT',
      data,
      header: { ..._headers(), ...header },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

