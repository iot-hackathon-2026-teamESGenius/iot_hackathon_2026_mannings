<template>
	<view class="container">
		<AppNavBar title="我的" :show-back="true" :show-menu="false" />

		<scroll-view scroll-y class="main-content">
			<!-- 已登录用户 -->
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
			
			<!-- 访客模式 -->
			<view class="card guest-card" v-else-if="isGuest">
				<view class="guest-icon">
					<uni-icons type="person" size="48" color="#999"></uni-icons>
				</view>
				<view class="guest-title">访客模式</view>
				<view class="guest-desc">您正在以访客身份浏览，登录后可解锁更多功能</view>
				<view class="guest-features">
					<view class="feature-item">
						<uni-icons type="checkmarkempty" size="14" color="#0066CC"></uni-icons>
						<text>选择门店查看详细数据</text>
					</view>
					<view class="feature-item">
						<uni-icons type="checkmarkempty" size="14" color="#0066CC"></uni-icons>
						<text>导出报表和数据</text>
					</view>
					<view class="feature-item">
						<uni-icons type="checkmarkempty" size="14" color="#0066CC"></uni-icons>
						<text>访问订单管理功能</text>
					</view>
				</view>
				<button class="btn primary" @click="goLogin">登录解锁全部功能</button>
			</view>

			<!-- 未登录且非访客 -->
			<view class="card" v-else-if="!loading && !isGuest">
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
import { apiGet, apiPost, getToken, setToken, isGuestMode, setGuestMode } from '../utils/api.js'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		return {
			user: null,
			loading: true,
			loggingOut: false,
			isGuest: false
		}
	},
	onShow() {
		this.isGuest = isGuestMode()
		if (!this.isGuest) {
			this.validateToken()
		} else {
			this.loading = false
		}
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
			// 如果是访客模式，先清除访客状态
			if (this.isGuest) {
				setGuestMode(false)
			}
			uni.reLaunch({ url: '/pages/login' })
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
			// 跳转到登录页
			setTimeout(() => {
				uni.reLaunch({ url: '/pages/login' })
			}, 500)
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
		&.primary {
			background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
			color: #fff;
			box-shadow: 0 8rpx 24rpx rgba(0,102,204,0.3);
		}
	}
	&.guest-card {
		text-align: center;
		padding: 48rpx 32rpx;
		
		.guest-icon {
			margin-bottom: 24rpx;
		}
		.guest-title {
			font-size: 36rpx;
			font-weight: bold;
			color: #333;
			margin-bottom: 16rpx;
		}
		.guest-desc {
			font-size: 26rpx;
			color: #666;
			margin-bottom: 32rpx;
		}
		.guest-features {
			text-align: left;
			background: #f8fbff;
			border-radius: 12rpx;
			padding: 24rpx;
			margin-bottom: 32rpx;
			
			.feature-item {
				display: flex;
				align-items: center;
				gap: 12rpx;
				margin-bottom: 16rpx;
				font-size: 26rpx;
				color: #333;
				
				&:last-child {
					margin-bottom: 0;
				}
			}
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
