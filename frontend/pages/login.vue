<template>
	<view class="page">
		<view class="bg-decoration"></view>
		
		<view class="header">
			<view class="logo-wrap">
				<image class="logo" src="/static/img/store.png" mode="aspectFit"></image>
			</view>
			<text class="title">万宁门店管理系统</text>
			<text class="sub">Mannings Store SLA Optimization</text>
		</view>

		<view class="form">
			<view class="row">
				<view class="input-wrap">
					<uni-icons type="person" size="20" color="#0066CC"></uni-icons>
					<input
						v-model="username"
						class="input"
						placeholder="请输入用户名"
						placeholder-class="placeholder"
					/>
				</view>
			</view>
			<view class="row">
				<view class="input-wrap">
					<uni-icons type="locked" size="20" color="#0066CC"></uni-icons>
					<input
						v-model="password"
						type="password"
						class="input"
						placeholder="请输入密码"
						placeholder-class="placeholder"
					/>
				</view>
			</view>
			<view v-if="errorMsg" class="error-msg">
				<uni-icons type="info" size="14" color="#DC3545"></uni-icons>
				<text>{{ errorMsg }}</text>
			</view>
			<button class="btn primary" :loading="loading" @click="onLogin">登 录</button>
			
			<view class="divider">
				<view class="line"></view>
				<text>测试账号</text>
				<view class="line"></view>
			</view>
			
			<view class="test-accounts">
				<view class="account-item" @click="fillAccount('admin', 'admin123')">
					<text class="role">管理员</text>
					<text class="info">admin / admin123</text>
				</view>
				<view class="account-item" @click="fillAccount('logistics_admin', 'logistics123')">
					<text class="role">物流管理</text>
					<text class="info">logistics_admin / logistics123</text>
				</view>
				<view class="account-item" @click="fillAccount('store_manager', 'store123')">
					<text class="role">门店管理</text>
					<text class="info">store_manager / store123</text>
				</view>
			</view>
		</view>
		
		<view class="footer">
			<text>IoT Hackathon 2026 - Team ESGenius</text>
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
		fillAccount(username, password) {
			this.username = username
			this.password = password
			this.errorMsg = ''
		},
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
						uni.reLaunch({ url: '/pages/index/index' })
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
	background: linear-gradient(180deg, #e8f4fd 0%, #f4f7f9 40%);
	position: relative;
	overflow: hidden;
}
.bg-decoration {
	position: absolute;
	top: -200rpx;
	right: -200rpx;
	width: 500rpx;
	height: 500rpx;
	background: linear-gradient(135deg, rgba(0,102,204,0.1) 0%, rgba(0,136,221,0.05) 100%);
	border-radius: 50%;
}
.header {
	padding: calc(120rpx + var(--status-bar-height)) 40rpx 48rpx;
	text-align: center;
	
	.logo-wrap {
		width: 140rpx;
		height: 140rpx;
		margin: 0 auto 32rpx;
		background: #fff;
		border-radius: 32rpx;
		box-shadow: 0 8rpx 32rpx rgba(0,102,204,0.15);
		display: flex;
		align-items: center;
		justify-content: center;
		
		.logo {
			width: 80rpx;
			height: 80rpx;
		}
	}
}
.title { 
	font-size: 44rpx; 
	font-weight: bold; 
	color: #0066CC;
	display: block;
}
.sub { 
	display: block; 
	margin-top: 12rpx; 
	font-size: 26rpx; 
	color: #666; 
	letter-spacing: 1rpx;
}
.form {
	padding: 0 48rpx;
	
	.row {
		margin-bottom: 28rpx;
	}
	
	.input-wrap {
		display: flex;
		align-items: center;
		background: #fff;
		border-radius: 20rpx;
		padding: 0 28rpx;
		height: 100rpx;
		box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.04);
		border: 2rpx solid transparent;
		transition: border-color 0.2s;
		
		&:focus-within {
			border-color: #0066CC;
		}
		
		.input {
			flex: 1;
			height: 100%;
			margin-left: 20rpx;
			font-size: 30rpx;
		}
	}
	
	.placeholder { color: #bbb; }
	
	.error-msg {
		display: flex;
		align-items: center;
		gap: 8rpx;
		margin-bottom: 20rpx;
		font-size: 26rpx;
		color: #DC3545;
		padding-left: 8rpx;
	}
	
	.btn {
		width: 100%;
		height: 100rpx;
		line-height: 100rpx;
		text-align: center;
		border-radius: 20rpx;
		font-size: 34rpx;
		font-weight: 500;
		letter-spacing: 8rpx;
		&.primary {
			background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
			color: #fff;
			box-shadow: 0 8rpx 24rpx rgba(0,102,204,0.3);
		}
	}
	
	.divider {
		display: flex;
		align-items: center;
		margin: 48rpx 0 32rpx;
		
		.line {
			flex: 1;
			height: 1px;
			background: #ddd;
		}
		
		text {
			padding: 0 24rpx;
			font-size: 24rpx;
			color: #999;
		}
	}
	
	.test-accounts {
		.account-item {
			display: flex;
			justify-content: space-between;
			align-items: center;
			padding: 24rpx 28rpx;
			background: #fff;
			border-radius: 16rpx;
			margin-bottom: 16rpx;
			box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
			
			&:active {
				background: #f5f5f5;
			}
			
			.role {
				font-size: 26rpx;
				color: #0066CC;
				font-weight: 500;
				background: #e8f4fd;
				padding: 8rpx 20rpx;
				border-radius: 8rpx;
			}
			
			.info {
				font-size: 24rpx;
				color: #666;
				font-family: monospace;
			}
		}
	}
}

.footer {
	position: absolute;
	bottom: 60rpx;
	left: 0;
	right: 0;
	text-align: center;
	font-size: 22rpx;
	color: #999;
}
</style>
