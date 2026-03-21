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
					<view class="entry-item orange shadow" @click="navTo('/pages/index/orders')">
						<uni-icons type="list" size="32" color="#fff"></uni-icons>
						<text>订单管理</text>
					</view>
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

		<!-- 门店选择模态框 -->
		<view v-if="showStoreModal" class="modal-overlay" @click.self="closeStoreModal">
			<view class="store-modal" @click.stop>
				<view class="modal-header">
					<text class="modal-title">选择门店</text>
					<view class="close-btn" @click="closeStoreModal">
						<uni-icons type="close" size="20" color="#666"></uni-icons>
					</view>
				</view>
				<view class="search-box">
					<input 
						class="search-input" 
						v-model="storeSearchText" 
						placeholder="搜索门店名称、ID或地区"
						@input="onStoreSearch"
					/>
					<uni-icons type="search" size="18" color="#999" class="search-icon"></uni-icons>
				</view>
				<scroll-view scroll-y class="store-list">
					<view class="store-item" @click="selectAllStores">
						<view class="store-info">
							<text class="store-name">全部门店</text>
							<text class="store-detail">显示所有门店的数据</text>
						</view>
					</view>
					<view 
						v-for="store in displayedStores" 
						:key="store.store_id"
						class="store-item"
						@click="selectStore(store)"
					>
						<view class="store-info">
							<text class="store-name">{{ store.store_name }}</text>
							<text class="store-detail">ID: {{ store.store_id }} · {{ store.district || '未知地区' }}</text>
						</view>
					</view>
					<view v-if="!displayedStores.length && storeSearchText" class="no-result">
						<text>未找到匹配的门店</text>
					</view>
					<view v-if="hasMoreStores" class="load-more" @click="loadMoreStores">
						<text>加载更多 ({{ filteredStoreList.length - displayedStores.length }} 个)</text>
					</view>
				</scroll-view>
			</view>
		</view>

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
			currentShopName: '全部门店',
			// 当前用户可访问的门店列表（用于下拉）
			storeList: [],
			// 门店选择模态框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20, // 初始显示的门店数量
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
	computed: {
		// 过滤后的门店列表（根据搜索文本）
		filteredStoreList() {
			if (!this.storeSearchText.trim()) {
				return this.storeList
			}
			const searchText = this.storeSearchText.toLowerCase()
			return this.storeList.filter(store => {
				return store.store_name.toLowerCase().includes(searchText) ||
					   store.store_id.toLowerCase().includes(searchText) ||
					   (store.district && store.district.toLowerCase().includes(searchText))
			})
		},
		// 当前显示的门店列表（分页显示）
		displayedStores() {
			return this.filteredStoreList.slice(0, this.displayLimit)
		},
		// 是否还有更多门店
		hasMoreStores() {
			return this.filteredStoreList.length > this.displayLimit
		}
	},
	onLoad() {
		const userInfo = getUserInfo()
		this.menuItems = getVisibleMenuItems(userInfo)
		// 不要直接使用缓存的门店名称，等待fetchStoreListThenData()更新
		this.currentShopName = '全部门店'
		this.fetchStoreListThenData()
	},
	onShow() {
		// 从其他页返回时同步选中门店显示
		const selected = getSelectedStore()
		if (selected) {
			// 检查选中的门店是否在当前门店列表中，如果不在则重新获取
			if (this.storeList.length > 0) {
				const foundStore = this.storeList.find(store => store.store_id === selected.store_id)
				if (foundStore) {
					this.currentShopName = foundStore.store_name
				} else {
					this.currentShopName = selected.store_name
				}
			} else {
				this.currentShopName = selected.store_name
			}
		}
		this.menuItems = getVisibleMenuItems(getUserInfo())
	},
	methods: {
		/** 拉取可访问门店列表（需已登录）；若无选中门店则选第一个，再拉首页数据 */
		async fetchStoreListThenData() {
			// 清除旧的门店缓存
			uni.removeStorageSync('mannings_selected_store')
			
			// 加载门店列表（与需求预测页面使用相同的逻辑）
			await this.loadStoreOptions()
			
			// 默认选择"全部门店"，与需求预测页面保持一致
			setSelectedStore('', '全部门店')
			this.currentShopName = '全部门店'
			
			// 处理用户登录状态
			if (getToken()) {
				// 若本地无用户信息（如清除过缓存），从 validate 恢复
				if (!getUserInfo()) {
					try {
						const res = await apiGet('/auth/validate')
						if (res && res.valid && res.user) setUserInfo(res.user)
					} catch (e) {}
				}
				this.menuItems = getVisibleMenuItems(getUserInfo())
			}
			
			this.loadDashboardData()
		},
		/** 导航栏点击：弹出门店下拉选择 */
		openStorePicker() {
			if (!this.storeList.length) {
				uni.showToast({ title: '暂无可选门店', icon: 'none' })
				return
			}
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
			this.displayLimit = 20 // 重置显示限制
		},
		selectStore(store) {
			setSelectedStore(store.store_id, store.store_name)
			this.currentShopName = store.store_name
			this.closeStoreModal()
			this.loadDashboardData()
		},
		selectAllStores() {
			// 首页选择"全部门店"时，显示为"全部门店"但不设置具体门店ID
			setSelectedStore('', '全部门店')
			this.currentShopName = '全部门店'
			this.closeStoreModal()
			this.loadDashboardData()
		},
		onStoreSearch() {
			// 搜索输入处理，computed属性会自动更新filteredStoreList
			this.displayLimit = 20 // 重置显示限制
		},
		loadMoreStores() {
			this.displayLimit += 20 // 每次加载20个更多门店
		},
		async loadStoreOptions() {
			try {
				// 使用公开API获取门店列表（与需求预测页面完全相同的逻辑）
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回的原始格式
					this.storeList = res.data
				}
			} catch (e) {
				console.error('加载门店列表失败', e)
				// 保持空数组，不使用模拟数据
				this.storeList = []
			}
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
			// 映射为前端展示结构（兼容真实数据和模拟数据）
			this.stats = [
				{
					label: 'SLA 达成率',
					value: `${d.sla_achievement_rate?.value || 0}${d.sla_achievement_rate?.unit || '%'}`,
					sub: d.sla_achievement_rate?.change ? `较昨日 ${d.sla_achievement_rate.change}${d.sla_achievement_rate.unit}` : '历史数据',
					type: d.sla_achievement_rate?.trend === 'up' ? 'normal' : 'low'
				},
				{
					label: '总订单数',
					value: `${d.total_orders?.value || d.today_orders?.value || 0}${d.total_orders?.unit || d.today_orders?.unit || '单'}`,
					sub: d.total_orders?.description || '历史累计',
					type: 'normal'
				},
				{
					label: '完成订单',
					value: `${d.completed_orders?.value || 0}${d.completed_orders?.unit || '单'}`,
					sub: d.cancel_rate ? `取消率 ${d.cancel_rate.value}%` : '',
					type: 'normal'
				},
				{
					label: '平均履约时间',
					value: `${d.avg_fulfillment_time?.value || d.avg_pickup_time?.value || 0}${d.avg_fulfillment_time?.unit || d.avg_pickup_time?.unit || '小时'}`,
					sub: d.active_stores ? `活跃门店 ${d.active_stores.value} 家` : '',
					type: d.avg_fulfillment_time?.trend === 'down' ? 'normal' : 'low'
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
			&.orange { background: linear-gradient(135deg, #FD7E14 0%, #FF9500 100%); }
			&.shadow { box-shadow: 0 8rpx 20rpx rgba(0,0,0,0.08); }
			text { margin-top: 16rpx; font-size: 28rpx; font-weight: bold; }
		}
	}
}

/* 门店选择模态框样式 */
.modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 1000;
	padding: 40rpx;
}

.store-modal {
	width: 100%;
	max-width: 600rpx;
	max-height: 80vh;
	background: #fff;
	border-radius: 20rpx;
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.modal-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 30rpx 40rpx;
	border-bottom: 1px solid #f0f0f0;
	
	.modal-title {
		font-size: 32rpx;
		font-weight: bold;
		color: #333;
	}
	
	.close-btn {
		padding: 10rpx;
		cursor: pointer;
	}
}

.search-box {
	position: relative;
	margin: 20rpx 40rpx;
	
	.search-input {
		width: 100%;
		height: 80rpx;
		padding: 0 50rpx 0 20rpx;
		border: 1px solid #e0e0e0;
		border-radius: 40rpx;
		font-size: 28rpx;
		background: #f8f9fa;
		box-sizing: border-box;
	}
	
	.search-icon {
		position: absolute;
		right: 20rpx;
		top: 50%;
		transform: translateY(-50%);
	}
}

.store-list {
	flex: 1;
	max-height: 500rpx;
}

.store-item {
	padding: 24rpx 40rpx;
	border-bottom: 1px solid #f5f5f5;
	cursor: pointer;
	
	&:hover {
		background: #f8f9fa;
	}
	
	&:active {
		background: #e9ecef;
	}
}

.store-info {
	.store-name {
		display: block;
		font-size: 30rpx;
		color: #333;
		font-weight: 500;
		margin-bottom: 8rpx;
	}
	
	.store-detail {
		display: block;
		font-size: 24rpx;
		color: #666;
	}
}

.no-result {
	padding: 60rpx 40rpx;
	text-align: center;
	color: #999;
	font-size: 28rpx;
}

.load-more {
	padding: 30rpx 40rpx;
	text-align: center;
	color: #0066CC;
	font-size: 28rpx;
	border-top: 1px solid #f5f5f5;
	cursor: pointer;
	
	&:active {
		background: #f8f9fa;
	}
}
</style>