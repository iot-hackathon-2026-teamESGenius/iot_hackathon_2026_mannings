<script>
import { getToken, getUserInfo, setToken, setUserInfo, apiGet, isGuestMode } from './utils/api.js'
import { canAccessPage } from './utils/permission.js'

// 访客模式允许访问的页面（只读）
const GUEST_ALLOWED_PAGES = [
	'/pages/login',
	'/pages/index/index',
	'/pages/index/forcast',
	'/pages/index/replenishment',
	'/pages/index/deliever_map',
	'/pages/my'
]

export default {
	onLaunch: function() {
		console.log('App Launch')
		this.checkLoginStatus()
		this.setupRouteInterceptor()
	},
	onShow: function() {
		console.log('App Show')
	},
	onHide: function() {
		console.log('App Hide')
	},
	methods: {
		// 检查登录状态
		async checkLoginStatus() {
			const token = getToken()
			const userInfo = getUserInfo()
			const guestMode = isGuestMode()
			
			// 访客模式直接进入首页
			if (guestMode) {
				setTimeout(() => {
					uni.reLaunch({ url: '/pages/index/index' })
				}, 100)
				return
			}
			
			if (token && userInfo) {
				// 已登录，验证token有效性
				try {
					const res = await apiGet('/auth/validate')
					if (res && res.valid) {
						// token有效，跳转首页
						setTimeout(() => {
							uni.reLaunch({ url: '/pages/index/index' })
						}, 100)
						return
					}
				} catch (e) {
					console.log('Token验证失败，清除登录状态')
				}
				// token无效，清除登录状态
				setToken(null)
				setUserInfo(null)
			}
			// 未登录，停留在登录页
		},
		
		// 设置路由拦截器
		setupRouteInterceptor() {
			const whiteList = ['/pages/login']
			
			// 拦截 navigateTo
			const originalNavigateTo = uni.navigateTo
			uni.navigateTo = (options) => {
				if (this.checkAuth(options.url, whiteList)) {
					return originalNavigateTo.call(uni, options)
				}
			}
			
			// 拦截 redirectTo
			const originalRedirectTo = uni.redirectTo
			uni.redirectTo = (options) => {
				if (this.checkAuth(options.url, whiteList)) {
					return originalRedirectTo.call(uni, options)
				}
			}
			
			// 拦截 reLaunch
			const originalReLaunch = uni.reLaunch
			uni.reLaunch = (options) => {
				if (this.checkAuth(options.url, whiteList)) {
					return originalReLaunch.call(uni, options)
				}
			}
			
			// 拦截 switchTab
			const originalSwitchTab = uni.switchTab
			uni.switchTab = (options) => {
				if (this.checkAuth(options.url, whiteList)) {
					return originalSwitchTab.call(uni, options)
				}
			}
		},
		
		// 检查权限
		checkAuth(url, whiteList) {
			if (!url) return true
			
			// 提取路径（去除参数）
			const path = url.split('?')[0]
			
			// 白名单放行
			if (whiteList.some(w => path.includes(w))) {
				return true
			}
			
			// 检查登录状态
			const token = getToken()
			const userInfo = getUserInfo()
			const guestMode = isGuestMode()
			
			// 访客模式：只允许访问特定页面
			if (guestMode) {
				if (GUEST_ALLOWED_PAGES.some(p => path.includes(p))) {
					return true
				}
				uni.showToast({ title: '请先登录后访问', icon: 'none' })
				return false
			}
			
			if (!token || !userInfo) {
				uni.showToast({ title: '请先登录', icon: 'none' })
				setTimeout(() => {
					uni.reLaunch({ url: '/pages/login' })
				}, 500)
				return false
			}
			
			// 检查页面权限
			if (!canAccessPage(path, userInfo)) {
				uni.showToast({ title: '无权访问该页面', icon: 'none' })
				return false
			}
			
			return true
		}
	}
}
</script>

<style>
	/*每个页面公共css */
</style>
