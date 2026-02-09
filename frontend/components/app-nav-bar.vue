<template>
	<view class="nav-bar">
		<view class="nav-left" @click="onLeft">
			<uni-icons v-if="showBack" type="back" size="24" color="#fff"></uni-icons>
			<uni-icons v-else-if="showMenu" type="bars" size="24" color="#fff"></uni-icons>
			<view v-else class="nav-placeholder"></view>
		</view>
		<view class="nav-title">
			<uni-icons v-if="showMenu" type="location-filled" size="18" color="#fff"></uni-icons>
			<text class="nav-text">{{ title }}</text>
		</view>
		<view class="nav-right" @click="onMy">
			<uni-icons type="person" size="24" color="#fff"></uni-icons>
		</view>
	</view>
</template>

<script>
export default {
	name: 'AppNavBar',
	props: {
		title: { type: String, default: '' },
		showBack: { type: Boolean, default: true },
		showMenu: { type: Boolean, default: false }
	},
	methods: {
		onLeft() {
			if (this.showBack) this.$emit('back')
			if (this.showMenu) this.$emit('menu')
		},
		onMy() {
			this.$emit('my')
			uni.switchTab({ url: '/pages/my' })
		}
	}
}
</script>

<style lang="scss" scoped>
.nav-bar {
	height: 88rpx;
	padding-top: var(--status-bar-height);
	background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-left: 30rpx;
	padding-right: 30rpx;
	padding-bottom: 0;
	color: #fff;
	position: sticky;
	top: 0;
	left: 0;
	right: 0;
	z-index: 100;
	box-shadow: 0 2rpx 10rpx rgba(0, 102, 204, 0.25);
}
.nav-left,
.nav-right {
	width: 80rpx;
	display: flex;
	align-items: center;
}
.nav-right {
	justify-content: flex-end;
}
.nav-placeholder {
	width: 24rpx;
	height: 24rpx;
}
.nav-title {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	.nav-text {
		margin-left: 10rpx;
		font-size: 30rpx;
		font-weight: bold;
	}
}
</style>
