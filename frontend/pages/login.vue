<template>
	<view class="page">
		<view class="header">
			<text class="title">万宁门店管理系统</text>
			<text class="sub">登录后使用完整功能</text>
		</view>

		<view class="form">
			<view class="row">
				<text class="label">用户名</text>
				<input
					v-model="username"
					class="input"
					placeholder="store_manager / logistics_admin / admin"
					placeholder-class="placeholder"
				/>
			</view>
			<view class="row">
				<text class="label">密码</text>
				<input
					v-model="password"
					type="password"
					class="input"
					placeholder="对应密码见下"
					placeholder-class="placeholder"
				/>
			</view>
			<view v-if="errorMsg" class="error-msg">{{ errorMsg }}</view>
			<button class="btn primary" :loading="loading" @click="onLogin">登录</button>
			<view class="tips">
				<text>测试账号看src\api\routers\auth.py</text>
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
			errorMsg: ''
		}
	},
	methods: {
		async onLogin() {
			if (!this.username.trim() || !this.password.trim()) {
				this.errorMsg = '请输入用户名和密码'
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
					// 保存用户信息（含 permissions、store_ids）供权限与门店筛选使用
					const userInfo = res.user ? { ...res.user, permissions: res.permissions || [] } : null
					setUserInfo(userInfo)
					uni.showToast({ title: '登录成功', icon: 'success' })
					setTimeout(() => {
						uni.switchTab({ url: '/pages/index/index' })
					}, 500)
				} else {
					this.errorMsg = (res && res.error) || '登录失败'
				}
			} catch (e) {
				console.error('登录失败', e)
				this.errorMsg = '网络错误或后端未启动'
				uni.showToast({ title: '登录失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		}
	}
}
</script>

<style lang="scss" scoped>
.page {
	min-height: 100vh;
	background: #f4f7f9;
	padding-top: calc(80rpx + var(--status-bar-height));
}
.header {
	padding: 0 40rpx 64rpx;
	text-align: center;
}
.title { font-size: 40rpx; font-weight: bold; color: #333; }
.sub { display: block; margin-top: 16rpx; font-size: 28rpx; color: #666; }
.form {
	padding: 0 40rpx;
	.row {
		margin-bottom: 32rpx;
		.label {
			display: block;
			margin-bottom: 12rpx;
			font-size: 28rpx;
			color: #333;
		}
		.input {
			width: 100%;
			height: 88rpx;
			padding: 0 24rpx;
			background: #fff;
			border-radius: 16rpx;
			font-size: 28rpx;
			box-sizing: border-box;
		}
		.placeholder { color: #999; }
	}
	.error-msg {
		margin-bottom: 20rpx;
		font-size: 26rpx;
		color: #DC3545;
	}
	.btn {
		width: 100%;
		height: 88rpx;
		line-height: 88rpx;
		text-align: center;
		border-radius: 16rpx;
		font-size: 32rpx;
		&.primary {
			background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
			color: #fff;
		}
	}
	.tips {
		margin-top: 48rpx;
		padding: 24rpx;
		background: #fff;
		border-radius: 16rpx;
		font-size: 26rpx;
		color: #666;
	}
}
</style>
