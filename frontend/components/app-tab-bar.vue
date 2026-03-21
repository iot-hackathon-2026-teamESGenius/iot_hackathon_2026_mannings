<template>
	<view class="tab-bar-placeholder"></view>
	<view class="custom-tab-bar">
		<view class="tab-item" :class="{ active: isActive('/pages/index/index') }" @click="navTo('/pages/index/index')">
			<uni-icons :type="isActive('/pages/index/index') ? 'home-filled' : 'home'" size="24" :color="isActive('/pages/index/index') ? '#0066CC' : '#999'"></uni-icons>
			<text>首页</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/forcast') }" @click="navTo('/pages/index/forcast')">
			<uni-icons :type="isActive('/pages/index/forcast') ? 'eye-filled' : 'eye'" size="24" :color="isActive('/pages/index/forcast') ? '#0066CC' : '#999'"></uni-icons>
			<text>需求预测</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/replenishment') }" @click="navTo('/pages/index/replenishment')">
			<uni-icons :type="isActive('/pages/index/replenishment') ? 'cart-filled' : 'cart'" size="24" :color="isActive('/pages/index/replenishment') ? '#0066CC' : '#999'"></uni-icons>
			<text>补货</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/deliever_map') }" @click="navTo('/pages/index/deliever_map')">
			<uni-icons :type="isActive('/pages/index/deliever_map') ? 'location-filled' : 'location'" size="24" :color="isActive('/pages/index/deliever_map') ? '#0066CC' : '#999'"></uni-icons>
			<text>调度</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/my') }" @click="navTo('/pages/my')">
			<uni-icons :type="isActive('/pages/my') ? 'person-filled' : 'person'" size="24" :color="isActive('/pages/my') ? '#0066CC' : '#999'"></uni-icons>
			<text>我的</text>
		</view>
	</view>
</template>

<script>
export default {
	name: 'AppTabBar',
	data() {
		return {
			currentPath: ''
		}
	},
	onLoad() {
		this.getCurrentPath()
	},
	onShow() {
		this.getCurrentPath()
	},
	methods: {
		getCurrentPath() {
			const pages = getCurrentPages()
			if (pages.length > 0) {
				this.currentPath = pages[pages.length - 1].route
			}
		},
		isActive(path) {
			return this.currentPath === path.replace('/pages', 'pages')
		},
		navTo(url) {
			console.log('Navigating to:', url)
			// 使用 reLaunch 确保页面切换正常
			uni.reLaunch({
				url: url,
				success: function(res) {
					console.log('Navigation success:', res)
				},
				fail: function(err) {
					console.log('reLaunch failed, trying navigateTo:', err)
					uni.navigateTo({
						url: url,
						success: function(res) {
							console.log('NavigateTo success:', res)
						},
						fail: function(err) {
							console.log('NavigateTo failed:', err)
						}
					})
				}
			})
		}
	}
}
</script>

<style lang="scss" scoped>
.tab-bar-placeholder {
	height: 120rpx;
}
.custom-tab-bar {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	height: 100rpx;
	background: #ffffff;
	display: flex;
	align-items: center;
	justify-content: space-around;
	border-top: 1rpx solid #eee;
	z-index: 99;
	box-shadow: 0 -2rpx 10rpx rgba(0, 0, 0, 0.05);
}
.tab-item {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 12rpx 0;
	transition: all 0.2s ease;
	
	text {
		font-size: 22rpx;
		margin-top: 6rpx;
		color: #999;
		transition: color 0.2s ease;
	}
	
	&.active {
		text {
			color: #0066CC;
			font-weight: 500;
		}
	}
	
	&:active {
		opacity: 0.7;
	}
}
</style>
