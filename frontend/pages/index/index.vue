<template>
	<view class="container">
		<view class="nav-bar">
			<view class="nav-left" @click="showDrawer">
				<uni-icons type="bars" size="24" color="#fff"></uni-icons>
			</view>
				<view class="nav-title nav-title-btn" @click="openStorePicker">
				<uni-icons type="location-filled" size="18" color="#fff"></uni-icons>
				<text class="shop-name">{{ currentShopName }}</text>
				<uni-icons type="bottom" size="14" color="#fff"></uni-icons>
			</view>
			<view class="nav-right" @click="goMyPage">
				<uni-icons type="person" size="24" color="#fff"></uni-icons>
			</view>
		</view>
		<uni-drawer ref="leftDrawer" mode="left" :width="260">
			<view class="drawer-content">
				<view class="drawer-header">
					<view class="logo-box">DFI</view>
					<text class="brand">万宁门店管理系统</text>
				</view>
				<uni-list :border="false">
					<uni-list-item
						v-for="item in menuItems"
						:key="item.path"
						:title="item.title"
						showExtraIcon
						:extraIcon="item.extraIcon"
						@click="navTo(item.path)"
					/>
				</uni-list>
			</view>
		</uni-drawer>

		<scroll-view scroll-y class="main-content">
			<uni-section title="核心指标" type="line" padding>
				<view class="stats-grid">
					<view class="stat-card" v-for="(item, index) in stats" :key="index">
						<text class="label">{{ item.label }}</text>
						<text class="value">{{ item.value }}</text>
						<view class="trend-tag" :class="item.type">{{ item.sub }}</view>
					</view>
				</view>
			</uni-section>

			<uni-section title="SLA 优化趋势预测" type="line" padding>
				<view class="charts-box">
					<qiun-data-charts 
						type="area" 
						:opts="chartOpts" 
						:chartData="localChartData" 
						:canvas2d="true"
					/>
				</view>
			</uni-section>

			<uni-section title="实时预警" type="line" padding>
				<view class="warn-box">
					<uni-notice-bar 
						v-for="(item, i) in warnings" 
						:key="i" 
						show-icon 
						:speed="50"
						:text="item.text" 
						background-color="#fff" 
						:class="['warn-item', `warn-${item.risk_level}`]"
					/>
				</view>
			</uni-section>

			<uni-section title="快捷入口" type="line" padding>
				<view class="quick-entry">
					<view class="entry-item blue shadow" @click="handleAction('导出报表')">
						<uni-icons type="download" size="32" color="#fff"></uni-icons>
						<text>导出库存报表</text>
					</view>
					<view class="entry-item green shadow" @click="handleAction('查询SKU')">
						<uni-icons type="search" size="32" color="#fff"></uni-icons>
						<text>SKU 库存查询</text>
					</view>
				</view>
			</uni-section>
			
			<view style="height: 40rpx;"></view>
		</scroll-view>

		<view class="tab-bar-placeholder"></view>
		<AppTabBar />
	</view>
</template>

<script>
import { apiGet, getToken, getUserInfo, getSelectedStore, setSelectedStore, setUserInfo } from '../../utils/api.js'
import { getVisibleMenuItems } from '../../utils/permission.js'
import AppTabBar from '../../components/app-tab-bar.vue'

export default {
	components: { AppTabBar },
	data() {
		return {
			// 当前门店名（导航栏下拉选择）
			currentShopName: '请选择门店',
			// 当前用户可访问的门店列表（用于下拉）
			storeList: [],
			// 侧栏菜单项（按权限过滤）
			menuItems: [],

			// 首页核心指标（从 /api/dashboard/kpi 获取）
			stats: [],

			// 实时预警文案（从 /api/dashboard/alerts-summary 获取）
			warnings: [],

			// uCharts 图表配置与数据（从 /api/dashboard/trend 获取）
			localChartData: {
				categories: [],
				series: [
					{ name: 'SLA 达成率', data: [] }
				]
			},
			chartOpts: {
				color: ['#0066CC', '#FD7E14'],
				padding: [15, 10, 0, 15],
				dataLabel: false,
				legend: { position: 'top', float: 'right' },
				xAxis: { disableGrid: true, axisLineColor: '#eeeeee' },
				yAxis: { gridType: 'dash', dashLength: 2, gridColor: '#cccccc' },
				extra: {
					area: { type: 'straight', opacity: 0.2, addLine: true, gradient: true }
				}
			},

			loading: false,
			errorMsg: ''
		}
	},
	onLoad() {
		const userInfo = getUserInfo()
		this.menuItems = getVisibleMenuItems(userInfo)
		const selected = getSelectedStore()
		if (selected) this.currentShopName = selected.store_name
		else this.currentShopName = '请选择门店'
		this.fetchStoreListThenData()
	},
	onShow() {
		// 从其他页返回时同步选中门店显示
		const selected = getSelectedStore()
		if (selected) this.currentShopName = selected.store_name
		this.menuItems = getVisibleMenuItems(getUserInfo())
	},
	methods: {
		/** 拉取可访问门店列表（需已登录）；若无选中门店则选第一个，再拉首页数据 */
		async fetchStoreListThenData() {
			if (getToken()) {
				// 若本地无用户信息（如清除过缓存），从 validate 恢复
				if (!getUserInfo()) {
					try {
						const res = await apiGet('/auth/validate')
						if (res && res.valid && res.user) setUserInfo(res.user)
					} catch (e) {}
				}
				this.menuItems = getVisibleMenuItems(getUserInfo())
				try {
					const res = await apiGet('/auth/stores', { params: {} })
					if (res && res.success && res.data && res.data.length) {
						this.storeList = res.data
						const selected = getSelectedStore()
						if (!selected && this.storeList.length) {
							const first = this.storeList[0]
							setSelectedStore(first.store_id, first.store_name)
							this.currentShopName = first.store_name
						}
					}
				} catch (e) {
					console.error('获取门店列表失败', e)
				}
			}
			this.loadDashboardData()
		},
		/** 导航栏点击：弹出门店下拉选择 */
		openStorePicker() {
			if (!this.storeList.length) {
				uni.showToast({ title: '暂无可选门店', icon: 'none' })
				return
			}
			const itemList = this.storeList.map(s => s.store_name)
			uni.showActionSheet({
				itemList,
				success: (res) => {
					const idx = res.tapIndex
					const s = this.storeList[idx]
					setSelectedStore(s.store_id, s.store_name)
					this.currentShopName = s.store_name
					this.loadDashboardData()
				}
			})
		},
		showDrawer() {
			this.$refs.leftDrawer.open()
		},
		goBack() {
			uni.navigateBack()
		},
		goMyPage() {
			uni.switchTab({ url: '/pages/my' })
		},
		navTo(url) {
			this.$refs.leftDrawer.close()
			if (url === '/pages/index/index') return
			uni.navigateTo({ url })
		},
		handleAction(name) {
			uni.showModal({ title: '提示', content: '您点击了：' + name })
		},

		// ========== 首页数据拉取 ==========
		async loadDashboardData() {
			this.loading = true
			this.errorMsg = ''
			try {
				await Promise.all([
					this.fetchKpiCards(),
					this.fetchTrendChart(),
					this.fetchAlertsSummary()
				])
			} catch (e) {
				console.error('加载首页数据失败', e)
				this.errorMsg = '首页数据加载失败，请确认后端服务是否已启动'
				uni.showToast({ title: '首页数据加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},

		// 2.1 KPI 卡片：/api/dashboard/kpi（支持 store_id 筛选当前门店）
		async fetchKpiCards() {
			const store = getSelectedStore()
			const res = await apiGet('/dashboard/kpi', {
				params: store && store.store_id ? { store_id: store.store_id } : {}
			})
			if (!res || !res.success || !res.data) return

			const d = res.data
			// 映射为前端展示结构（可按需增减字段）
			this.stats = [
				{
					label: 'SLA 达成率',
					value: `${d.sla_achievement_rate.value}${d.sla_achievement_rate.unit}`,
					sub: `较昨日 ${d.sla_achievement_rate.change}${d.sla_achievement_rate.unit}`,
					type: d.sla_achievement_rate.trend === 'up' ? 'normal' : 'low'
				},
				{
					label: '今日订单数',
					value: `${d.today_orders.value}${d.today_orders.unit}`,
					sub: `较昨日 ${d.today_orders.change}${d.today_orders.unit}`,
					type: 'normal'
				},
				{
					label: '缺货率',
					value: `${d.stockout_rate.value}${d.stockout_rate.unit}`,
					sub: `变化 ${d.stockout_rate.change}${d.stockout_rate.unit}`,
					// 缺货率下降是好事
					type: d.stockout_rate.trend === 'down' ? 'normal' : 'low'
				},
				{
					label: '延迟配送次数',
					value: `${d.delivery_delay_count.value}${d.delivery_delay_count.unit}`,
					sub: `变化 ${d.delivery_delay_count.change}${d.delivery_delay_count.unit}`,
					type: d.delivery_delay_count.trend === 'down' ? 'normal' : 'low'
				}
			]
		},

		// 2.2 趋势图：/api/dashboard/trend（支持 store_id 筛选）
		async fetchTrendChart() {
			const store = getSelectedStore()
			const params = { metric: 'sla_rate', days: 7 }
			if (store && store.store_id) params.store_id = store.store_id
			const res = await apiGet('/dashboard/trend', { params })
			if (!res || !res.success || !res.data) return

			const trends = res.data.trends || []
			this.localChartData = {
				categories: trends.map(item => (item.date || '').slice(5)), // 显示 MM-DD
				series: [
					{
						name: 'SLA 达成率',
						data: trends.map(item => item.value)
					}
				]
			}
		},

		// 2.3 实时预警摘要：/api/dashboard/alerts-summary
		async fetchAlertsSummary() {
			const store = getSelectedStore()
			const res = await apiGet('/dashboard/alerts-summary', {
				params: store && store.store_id ? { store_id: store.store_id } : {}
			})
			if (!res || !res.success || !res.data) return

			const alerts = res.data.alerts || []
			this.warnings = alerts.map(a => {
				const levelMap = {
					low: '低',
					medium: '中',
					high: '高',
					critical: '严重'
				}
				const levelText = levelMap[a.risk_level] || a.risk_level
				return {
					risk_level: a.risk_level,
					text: `【${levelText}】${a.title}：${a.description}`
				}
			})
		}
	}
}
</script>

<style lang="scss" scoped>
.container {
	background-color: #f4f7f9;
	min-height: 100vh;

	.nav-bar {
			height: 88rpx;
			padding-top: var(--status-bar-height);
			background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 0 30rpx;
			color: #fff;
			position: sticky;
			top: 0;
			z-index: 100;
			box-shadow: 0 2rpx 10rpx rgba(0,102,204,0.25);
	
			.nav-title {
				display: flex;
				align-items: center;
				.shop-name { margin-left: 10rpx; font-size: 30rpx; font-weight: bold; }
			}
			.nav-title-btn {
				cursor: pointer;
				.shop-name { margin-right: 8rpx; }
			}
		}
	
		.drawer-content {
			padding-top: var(--status-bar-height);
			.drawer-header {
				padding: 60rpx 40rpx;
				background: #f8fbff;
				display: flex;
				flex-direction: column;
				align-items: center;
				border-bottom: 1px solid #eee;
				.logo-box {
					width: 100rpx; height: 100rpx; background: #0066CC;
					border-radius: 20rpx; color: #fff; line-height: 100rpx;
					text-align: center; font-weight: bold; font-size: 40rpx;
				}
				.brand { margin-top: 20rpx; font-size: 28rpx; color: #333; font-weight: bold; }
			}
		}
	
		.main-content {
			height: calc(100vh - 88rpx - var(--status-bar-height) - 100rpx);
			padding: 0 30rpx;
			padding-bottom: 40rpx;
			box-sizing: border-box;
		}
	
		.stats-grid {
			display: flex;
			flex-wrap: wrap;
			padding: 16rpx;
			gap: 16rpx;
	
			.stat-card {
				width: calc(50% - 8rpx);
				background: #fff;
				padding: 28rpx 24rpx;
				border-radius: 20rpx;
				box-sizing: border-box;
				display: flex;
				flex-direction: column;
	
				.label { font-size: 26rpx; color: #999; }
				.value { font-size: 36rpx; font-weight: bold; color: #333; margin: 12rpx 0 8rpx; }
				.trend-tag {
					font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 30rpx; width: fit-content;
					&.normal { background: #e8f4fd; color: #0066CC; }
					&.low { background: #fff8e6; color: #FFC107; }
				}
			}
		}
	.charts-box {
		width: 100%;
		height: 500rpx;
		background: #fff;
		border-radius: 20rpx;
		padding: 24rpx 16rpx;
		margin-bottom: 8rpx;
	}

	.warn-box {
		.warn-item {
			margin-bottom: 16rpx;
			border-radius: 12rpx;
			border: 1px solid #eee;
		}
		.warn-low {
			color: #0066CC !important;
			border-color: #0066CC !important;
			background-color: #e8f4fd !important;
		}
		.warn-medium {
			color: #FFC107 !important;
			border-color: #FFC107 !important;
			background-color: #fff8e6 !important;
		}
		.warn-high {
			color: #FD7E14 !important;
			border-color: #FD7E14 !important;
			background-color: #fff3e0 !important;
		}
		.warn-critical {
			color: #DC3545 !important;
			border-color: #DC3545 !important;
			background-color: #ffebee !important;
		}
	}

	.quick-entry {
		display: flex;
		gap: 20rpx;
		padding: 8rpx 0;

		.entry-item {
			flex: 1;
			height: 220rpx;
			border-radius: 20rpx;
			display: flex;
			flex-direction: column;
			justify-content: center;
			align-items: center;
			color: #fff;
			&.blue { background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%); }
			&.green { background: linear-gradient(135deg, #2e7d32 0%, #43a047 100%); }
			&.shadow { box-shadow: 0 8rpx 20rpx rgba(0,0,0,0.08); }
			text { margin-top: 16rpx; font-size: 28rpx; font-weight: bold; }
		}
	}
}
</style>