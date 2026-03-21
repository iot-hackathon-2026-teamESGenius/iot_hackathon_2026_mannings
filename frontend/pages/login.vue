<template>
	<view class="page">
		<!-- 顶部区域 -->
		<view class="header">
			<image src="/static/logo.png" class="logo" mode="aspectFit" v-if="isDesktop" />
			<view class="header-content">
				<text class="title">Wanning Store Management</text>
			</view>
		</view>

		<!-- 登录表单 -->
		<view class="form-container">
			<view class="form-card">
				<view class="form-header">
					<text class="form-title">Sign In</text>
					<text class="form-subtitle">Welcome to Wanning Hong Kong</text>
				</view>

				<view class="form-fields">
					<!-- 用户名输入 -->
					<view class="input-group">
						<view class="input-label-row">
							<text class="input-label">Username</text>
							<text class="required-mark">*</text>
						</view>
						<view class="input-wrapper">
							<input
								v-model="username"
								class="input-field"
								placeholder="Enter your username"
								placeholder-class="placeholder"
								:disabled="loading"
								@confirm="onLogin"
							/>
						</view>
					</view>

					<!-- 密码输入 -->
					<view class="input-group">
						<view class="input-label-row">
							<text class="input-label">Password</text>
							<text class="required-mark">*</text>
						</view>
						<view class="input-wrapper">
							<input
								v-model="password"
								:password="true" 
								:type="showPassword ? 'text' : 'password'"
								class="input-field"
								placeholder="Enter your password"
								placeholder-class="placeholder"
								:disabled="loading"
								@confirm="onLogin"
							/>
<!-- 							<view 
								class="password-toggle" 
								@click="togglePasswordVisibility" 
								v-if="!loading && password"
							>
								<text class="toggle-icon">{{ showPassword ? '👁️' : '👁️‍🗨️' }}</text>
							</view> -->
						</view>
					</view>

					<!-- 错误信息 -->
					<view v-if="errorMsg" class="error-container">
						<text class="error-icon">⚠️</text>
						<text class="error-msg">{{ errorMsg }}</text>
					</view>

					<!-- 登录按钮 -->
					<button 
						class="login-button" 
						:class="{ 'loading': loading, 'disabled': !canLogin }" 
						:disabled="loading || !canLogin"
						@click="onLogin"
					>
						<view class="button-content">
							<text v-if="loading" class="loading-dots">...</text>
							<text v-else class="button-text">SIGN IN</text>
						</view>
					</button>

					<!-- 香港特色底部 -->
					<view class="hk-footer">
						<text class="hk-text">萬寧 您的健康夥伴</text>
						<text class="copyright">© 2026 Mannings Hong Kong</text>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { apiPost, setToken, setUserInfo } from '../utils/api.js'

export default {
	data() {
		return {
			username: '',
			password: '',
			loading: false,
			errorMsg: '',
			showPassword: false,
			isDesktop: false
		}
	},
	computed: {
		canLogin() {
			return this.username.trim() && this.password.trim()
		}
	},
	methods: {
		async onLogin() {
			if (!this.canLogin) {
				this.errorMsg = 'Please enter both username and password'
				return
			}
			
			this.loading = true
			this.errorMsg = ''
			
			try {
				const res = await apiPost('/auth/login', {
					username: this.username.trim(),
					password: this.password
				})
				
				if (res && res.success && res.token) {
					setToken(res.token)
					const userInfo = res.user ? { 
						...res.user, 
						permissions: res.permissions || [] 
					} : null
					setUserInfo(userInfo)
					
					uni.showToast({ 
						title: 'Login Successful', 
						icon: 'success',
						duration: 1500
					})
					
					setTimeout(() => {
						uni.switchTab({ url: '/pages/index/index' })
					}, 500)
				} else {
					this.errorMsg = (res && res.error) || 'Login failed. Please check your credentials.'
				}
			} catch (e) {
				console.error('Login error', e)
				this.errorMsg = e.message || 'Network error or server unavailable'
				uni.showToast({ 
					title: 'Login failed', 
					icon: 'none',
					duration: 2000
				})
			} finally {
				this.loading = false
			}
		},
		
		togglePasswordVisibility() {
			this.showPassword = !this.showPassword
		},
		
		checkScreenSize() {
			const systemInfo = uni.getSystemInfoSync()
			this.isDesktop = systemInfo.windowWidth >= 768
		}
	},
	
	onLoad() {
		this.checkScreenSize()
		// 监听屏幕旋转
		uni.onWindowResize(() => {
			this.checkScreenSize()
		})
	},
	
	onUnload() {
		uni.offWindowResize()
	}
}
</script>

<style lang="scss" scoped>
/* 响应式断点 */
$mobile-breakpoint: 768px;

/* 基础页面样式 */
.page {
	min-height: 100vh;
	background: #f8f9fa;
	display: flex;
	flex-direction: column;
	
	/* 桌面端样式 */
	@media (min-width: $mobile-breakpoint) {
		background: #ffffff;
		padding: 40px;
		min-height: calc(100vh - 80px);
		justify-content: center;
		align-items: center;
	}
}

/* 顶部区域 */
.header {
	padding: 40rpx 40rpx 20rpx;
	text-align: center;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 20rpx;
	
	@media (min-width: $mobile-breakpoint) {
		margin-bottom: 40px;
		padding: 0;
		justify-content: center;
	}
}

.logo {
	width: 60rpx;
	height: 60rpx;
	
	@media (min-width: $mobile-breakpoint) {
		width: 80rpx;
		height: 80rpx;
	}
}

.header-content {
	display: flex;
	flex-direction: column;
}

.title {
	font-size: 45rpx;
	font-weight: 700;
	color: #1a365d;
	letter-spacing: -0.5rpx;
	padding-bottom: 3%;
	padding-top: 3%;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 32px;
		letter-spacing: -1px;
	}
}

.sub {
	display: block;
	margin-top: 8rpx;
	font-size: 24rpx;
	color: #6c757d;
	font-weight: 500;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 16px;
		margin-top: 4px;
	}
}

/* 表单容器 */
.form-container {
	flex: 1;
	padding: 20rpx 40rpx 40rpx;
	
	@media (min-width: $mobile-breakpoint) {
		width: 420px;
		padding: 0;
	}
}

/* 表单卡片 */
.form-card {
	background: #ffffff;
	border-radius: 16rpx;
	padding: 40rpx 32rpx;
	box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
	
	@media (min-width: $mobile-breakpoint) {
		border-radius: 12px;
		padding: 48px 40px;
		box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
		border: 1px solid #e9ecef;
	}
}

.form-header {
	margin-bottom: 40rpx;
	text-align: center;
	
	@media (min-width: $mobile-breakpoint) {
		margin-bottom: 32px;
	}
}

.form-title {
	font-size: 40rpx;
	font-weight: 700;
	color: #212529;
	display: block;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 24px;
	}
}

.form-subtitle {
	display: block;
	margin-top: 8rpx;
	font-size: 24rpx;
	color: #6c757d;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 16px;
		margin-top: 4px;
	}
}

/* 输入框组 */
.input-group {
	margin-bottom: 32rpx;
	
	@media (min-width: $mobile-breakpoint) {
		margin-bottom: 24px;
	}
}

.input-label-row {
	display: flex;
	align-items: center;
	margin-bottom: 12rpx;
}

.input-label {
	font-size: 28rpx;
	font-weight: 600;
	color: #495057;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 16px;
	}
}

.required-mark {
	color: #dc3545;
	margin-left: 4rpx;
	font-size: 24rpx;
}

.input-wrapper {
	position: relative;
	display: flex;
	align-items: center;
	background: #ffffff;
	border: 2px solid #dee2e6;
	border-radius: 8rpx;
	padding: 0 20rpx;
	transition: all 0.2s ease;
	
	&:focus-within {
		border-color: #0066cc;
		box-shadow: 0 0 0 2px rgba(0, 102, 204, 0.1);
	}
	
	@media (min-width: $mobile-breakpoint) {
		border-radius: 6px;
		padding: 0 16px;
		height: 52px;
	}
}

.input-icon-container {
	margin-right: 16rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	
	@media (min-width: $mobile-breakpoint) {
		margin-right: 12px;
	}
}

.input-icon {
	font-size: 28rpx;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 20px;
	}
}

.input-field {
	flex: 1;
	height: 88rpx;
	font-size: 28rpx;
	color: #212529;
	background: transparent;
	
	&:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
	
	@media (min-width: $mobile-breakpoint) {
		height: auto;
		font-size: 16px;
		padding: 12px 0;
	}
}

.placeholder {
	color: #adb5bd;
	font-size: 28rpx;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 16px;
	}
}

.password-toggle {
	padding: 8rpx;
	cursor: pointer;
	user-select: none;
	
	@media (min-width: $mobile-breakpoint) {
		padding: 4px;
	}
}

.toggle-icon {
	font-size: 28rpx;
	opacity: 0.7;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 20px;
	}
}

/* 错误信息 */
.error-container {
	display: flex;
	align-items: center;
	background: #f8d7da;
	border: 1px solid #f5c6cb;
	border-radius: 8rpx;
	padding: 20rpx 24rpx;
	margin-bottom: 32rpx;
	
	@media (min-width: $mobile-breakpoint) {
		padding: 12px 16px;
		border-radius: 6px;
		margin-bottom: 24px;
	}
}

.error-icon {
	font-size: 28rpx;
	margin-right: 12rpx;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 20px;
	}
}

.error-msg {
	font-size: 24rpx;
	color: #721c24;
	flex: 1;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 16px;
	}
}

/* 登录按钮 */
.login-button {
	width: 100%;
	height: 96rpx;
	background: #0066cc;
	border-radius: 8rpx;
	border: none;
	color: white;
	font-size: 28rpx;
	font-weight: 600;
	margin-bottom: 32rpx;
	cursor: pointer;
	transition: all 0.2s ease;
	position: relative;
	overflow: hidden;
	
	&:hover:not(:disabled):not(.disabled) {
		background: #0056b3;
		transform: translateY(-2px);
		box-shadow: 0 4rpx 12rpx rgba(0, 102, 204, 0.3);
	}
	
	&:active:not(:disabled):not(.disabled) {
		transform: translateY(0);
	}
	
	&:disabled,
	&.disabled {
		opacity: 0.6;
		cursor: not-allowed;
		background: #6c757d;
	}
	
	&.loading {
		opacity: 0.8;
	}
	
	@media (min-width: $mobile-breakpoint) {
		height: 52px;
		border-radius: 6px;
		font-size: 18px;
		margin-bottom: 24px;
	}
}

.button-content {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 100%;
}

.loading-dots {
	font-size: 28rpx;
	font-weight: bold;
	animation: blink 1.4s infinite;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 20px;
	}
}

.button-text {
	color: white;
	font-weight: 600;
	letter-spacing: 1rpx;
}

@keyframes blink {
	0%, 20% { opacity: 0.2; }
	50% { opacity: 1; }
	100% { opacity: 0.2; }
}

/* 测试账号提示 */
.test-hint {
	display: flex;
	align-items: center;
	justify-content: center;
	background: #e9ecef;
	border-radius: 8rpx;
	padding: 20rpx 16rpx;
	margin-top: 24rpx;
	
	@media (min-width: $mobile-breakpoint) {
		padding: 12px 16px;
		border-radius: 6px;
		margin-top: 20px;
	}
}

.hint-icon {
	font-size: 24rpx;
	margin-right: 12rpx;
	opacity: 0.7;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 18px;
	}
}

.hint-text {
	font-size: 22rpx;
	color: #495057;
	text-align: center;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 14px;
	}
}

/* 香港特色底部 */
.hk-footer {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-top: 40rpx;
	padding-top: 20rpx;
	border-top: 1px solid #e9ecef;
	
	@media (min-width: $mobile-breakpoint) {
		margin-top: 32px;
		padding-top: 16px;
	}
}

.hk-text {
	font-size: 24rpx;
	color: #0066cc;
	font-weight: 600;
	margin-bottom: 8rpx;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 18px;
	}
}

.copyright {
	font-size: 20rpx;
	color: #6c757d;
	
	@media (min-width: $mobile-breakpoint) {
		font-size: 14px;
	}
}
</style>