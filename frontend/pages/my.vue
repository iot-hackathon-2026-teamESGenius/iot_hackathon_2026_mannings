<template>
	<view class="container">
		<AppNavBar title="我的" :show-back="true" :show-menu="false" />

		<scroll-view scroll-y class="main-content">
			<view class="card" v-if="user">
				<view class="row">
					<text class="label">用户</text>
					<text class="value">{{ user.username }}</text>
				</view>
				<view class="row">
					<text class="label">角色</text>
					<text class="value">{{ user.role }}</text>
				</view>
				<view class="row" v-if="user.store_ids && user.store_ids.length">
					<text class="label">门店</text>
					<text class="value">{{ user.store_ids.join(', ') }}</text>
				</view>
			</view>

			<view class="card" v-else-if="!loading">
				<view class="hint">未登录或 Token 已过期</view>
				<button class="btn" @click="goLogin">去登录</button>
			</view>

			<view class="card" v-if="user">
				<button class="btn logout" :loading="loggingOut" @click="onLogout">退出登录</button>
			</view>

			<view v-if="loading" class="hint">校验中...</view>
			<view class="tab-bar-placeholder"></view>
		</scroll-view>

		<AppTabBar />
	</view>
</template>

<script>
import AppNavBar from '../components/app-nav-bar.vue'
import AppTabBar from '../components/app-tab-bar.vue'
import { apiGet, apiPost, getToken, setToken } from '../utils/api.js'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		return {
			user: null,
			loading: true,
			loggingOut: false
		}
	},
	onShow() {
		this.validateToken()
	},
	methods: {
		async validateToken() {
			const token = getToken()
			if (!token) {
				this.user = null
				this.loading = false
				return
			}
			this.loading = true
			this.user = null
			try {
				const res = await apiGet('/auth/validate')
				if (res && res.valid && res.user) {
					this.user = res.user
				} else {
					setToken('')
				}
			} catch (e) {
				setToken('')
			} finally {
				this.loading = false
			}
		},
		goLogin() {
			uni.navigateTo({ url: '/pages/login' })
		},
		async onLogout() {
			this.loggingOut = true
			try {
				await apiPost('/auth/logout', {})
			} catch (e) {
				// 忽略网络错误，本地仍清除
			}
			setToken('')
			this.user = null
			uni.showToast({ title: '已退出', icon: 'none' })
			this.loggingOut = false
		}
	}
}
</script>

<style lang="scss" scoped>
.container {
	min-height: 100vh;
	background: #f4f7f9;
}
.main-content {
	height: calc(100vh - 88rpx - var(--status-bar-height) - 100rpx);
	padding: 0 30rpx;
	padding-bottom: 24rpx;
	box-sizing: border-box;
}
.tab-bar-placeholder {
	height: 120rpx;
}
.card {
	background: #fff;
	border-radius: 20rpx;
	padding: 28rpx 24rpx;
	margin-bottom: 24rpx;
	margin-top: 24rpx;
	box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.06);
	.row {
		display: flex;
		justify-content: space-between;
		margin-bottom: 18rpx;
		font-size: 28rpx;
		.label { color: #888; }
		.value { color: #333; }
	}
	.hint {
		text-align: center;
		padding: 24rpx 0;
		font-size: 28rpx;
		color: #666;
	}
	.btn {
		width: 100%;
		height: 84rpx;
		line-height: 84rpx;
		text-align: center;
		border-radius: 16rpx;
		font-size: 30rpx;
		background: #e8f4fd;
		color: #0066CC;
		margin-top: 24rpx;
		&.logout {
			background: #ffebee;
			color: #DC3545;
		}
	}
}
.hint {
	text-align: center;
	padding: 48rpx 24rpx;
	font-size: 28rpx;
	color: #666;
}
</style>
