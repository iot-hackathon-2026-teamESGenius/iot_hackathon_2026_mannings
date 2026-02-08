<template>
	<view class="tab-bar-placeholder"></view>
	<view class="custom-tab-bar">
		<view class="tab-item" :class="{ active: isActive('/pages/index/index') }" @click="navTo('/pages/index/index')">
			<uni-icons type="home" size="24" :color="isActive('/pages/index/index') ? '#0066CC' : '#999'"></uni-icons>
			<text>{{ isActive('/pages/index/index') ? '首页' : '首页' }}</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/forcast') }" @click="navTo('/pages/index/forcast')">
			<uni-icons type="eye" size="24" :color="isActive('/pages/index/forcast') ? '#0066CC' : '#999'"></uni-icons>
			<text>{{ isActive('/pages/index/forcast') ? '需求预测' : '需求预测' }}</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/replenishment') }" @click="navTo('/pages/index/replenishment')">
			<uni-icons type="cart" size="24" :color="isActive('/pages/index/replenishment') ? '#0066CC' : '#999'"></uni-icons>
			<text>{{ isActive('/pages/index/replenishment') ? '补货' : '补货' }}</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/index/deliever_map') }" @click="navTo('/pages/index/deliever_map')">
			<uni-icons type="location" size="24" :color="isActive('/pages/index/deliever_map') ? '#0066CC' : '#999'"></uni-icons>
			<text>{{ isActive('/pages/index/deliever_map') ? '调度' : '调度' }}</text>
		</view>
		<view class="tab-item" :class="{ active: isActive('/pages/my') }" @click="navTo('/pages/my')">
			<uni-icons type="person" size="24" :color="isActive('/pages/my') ? '#0066CC' : '#999'"></uni-icons>
			<text>{{ isActive('/pages/my') ? '我的' : '我的' }}</text>
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
			uni.switchTab({
				url: url,
				success: function(res) {
					console.log('Navigation success:', res)
				},
				fail: function(err) {
					console.log('Navigation failed:', err)
					// 如果 switchTab 失败，尝试使用 navigateTo
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
}
.tab-item {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 12rpx 0;
	text {
		font-size: 20rpx;
		margin-top: 6rpx;
		color: #999;
	}
	&.active {
		text {
			color: #0066CC;
		}
	}
}
</style>
