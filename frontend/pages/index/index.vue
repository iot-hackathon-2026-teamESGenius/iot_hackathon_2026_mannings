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
					<text class="brand">萬寧門店管理系統</text>
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
			<uni-section title="核心指標" type="line" padding>
				<view class="stats-grid">
					<view class="stat-card" v-for="(item, index) in stats" :key="index">
						<text class="label">{{ item.label }}</text>
						<text class="value">{{ item.value }}</text>
						<view class="trend-tag" :class="item.type">{{ item.sub }}</view>
					</view>
				</view>
			</uni-section>

			<uni-section title="SLA 優化趨勢預測" type="line" padding>
				<view class="charts-box">
					<qiun-data-charts 
						type="area" 
						:opts="chartOpts" 
						:chartData="localChartData" 
						:canvas2d="true"
					/>
				</view>
			</uni-section>

			<uni-section title="即時預警" type="line" padding>
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
					<view class="entry-item blue shadow" @click="handleAction('導出報表')">
						<uni-icons type="download" size="32" color="#fff"></uni-icons>
						<text>導出庫存報表</text>
					</view>
					<view class="entry-item green shadow" @click="handleAction('查詢SKU')">
						<uni-icons type="search" size="32" color="#fff"></uni-icons>
						<text>SKU 庫存查詢</text>
					</view>
				</view>
			</uni-section>
			
			<view style="height: 40rpx;"></view>
		</scroll-view>

		<!-- 门店选择模态框 -->
		<view v-if="showStoreModal" class="modal-overlay" @click.self="closeStoreModal">
			<view class="store-modal" @click.stop>
				<view class="modal-header">
					<text class="modal-title">選擇門店</text>
					<view class="close-btn" @click="closeStoreModal">
						<uni-icons type="close" size="20" color="#666"></uni-icons>
					</view>
				</view>
				<view class="search-box">
						<input 
						class="search-input" 
						v-model="storeSearchText" 
						placeholder="搜尋門店名稱、ID或地區"
						@input="onStoreSearch"
					/>
					<uni-icons type="search" size="18" color="#999" class="search-icon"></uni-icons>
				</view>
				<scroll-view scroll-y class="store-list">
					<view class="store-item" @click="selectAllStores">
						<view class="store-info">
							<text class="store-name">全部門店</text>
							<text class="store-detail">顯示所有門店的數據</text>
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
							<text class="store-detail">ID: {{ store.store_id }} · {{ store.district || '未知地區' }}</text>
						</view>
					</view>
					<view v-if="!displayedStores.length && storeSearchText" class="no-result">
						<text>未找到匹配的門店</text>
					</view>
					<view v-if="hasMoreStores" class="load-more" @click="loadMoreStores">
						<text>載入更多 ({{ filteredStoreList.length - displayedStores.length }} 個)</text>
					</view>
				</scroll-view>
			</view>
		</view>

<!-- 		<view class="tab-bar-placeholder"></view>
		<AppTabBar /> -->
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
			// 當前門店名（導航欄下拉選擇）
			currentShopName: '全部門店',
			// 當前使用者可訪問的門店列表（用於下拉）
			storeList: [],
			// 門店選擇模態框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20, // 初始顯示的門店數量
			// 側欄菜單項（按權限過濾）
			menuItems: [],

			// 首頁核心指標（從 /api/dashboard/kpi 獲取）
			stats: [],

			// 實時預警文案（從 /api/dashboard/alerts-summary 獲取）
			warnings: [],

			// uCharts 圖表配置與數據（從 /api/dashboard/trend 獲取）
			localChartData: {
				categories: [],
				series: [
					{ name: 'SLA 達成率', data: [] }
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
		// 過濾後的門店列表（根據搜尋文本）
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
		// 當前顯示的門店列表（分頁顯示）
		displayedStores() {
			return this.filteredStoreList.slice(0, this.displayLimit)
		},
		// 是否還有更多門店
		hasMoreStores() {
			return this.filteredStoreList.length > this.displayLimit
		}
	},
	onLoad() {
		const userInfo = getUserInfo()
		this.menuItems = getVisibleMenuItems(userInfo)
		// 不要直接使用緩存的門店名稱，等待fetchStoreListThenData()更新
		this.currentShopName = '全部門店'
		this.fetchStoreListThenData()
	},
	onShow() {
		// 從其他頁返回時同步選中門店顯示
		const selected = getSelectedStore()
		if (selected) {
			// 檢查選中的門店是否在當前門店列表中，如果不在則重新獲取
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
		/** 拉取可訪問門店列表（需已登入）；若無選中門店則選第一個，再拉首頁數據 */
		async fetchStoreListThenData() {
			// 清除舊的門店緩存
			uni.removeStorageSync('mannings_selected_store')
			
			// 加載門店列表（與需求預測頁面使用相同的邏輯）
			await this.loadStoreOptions()
			
			// 默認選擇"全部門店"，與需求預測頁面保持一致
			setSelectedStore('', '全部門店')
			this.currentShopName = '全部門店'
			
			// 處理使用者登入狀態
			if (getToken()) {
				// 若本地無使用者信息（如清除過緩存），從 validate 恢復
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
		/** 導航欄點擊：彈出門店下拉選擇 */
		openStorePicker() {
			if (!this.storeList.length) {
				uni.showToast({ title: '暫無可選門店', icon: 'none' })
				return
			}
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
			this.displayLimit = 20 // 重置顯示限制
		},
		selectStore(store) {
			setSelectedStore(store.store_id, store.store_name)
			this.currentShopName = store.store_name
			this.closeStoreModal()
			this.loadDashboardData()
		},
		selectAllStores() {
			// 首頁選擇"全部門店"時，顯示為"全部門店"但不設置具體門店ID
			setSelectedStore('', '全部門店')
			this.currentShopName = '全部門店'
			this.closeStoreModal()
			this.loadDashboardData()
		},
		onStoreSearch() {
			// 搜尋輸入處理，computed屬性會自動更新filteredStoreList
			this.displayLimit = 20 // 重置顯示限制
		},
		loadMoreStores() {
			this.displayLimit += 20 // 每次加載20個更多門店
		},
		async loadStoreOptions() {
			try {
				// 使用公開API獲取門店列表（與需求預測頁面完全相同的邏輯）
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回的原始格式
					this.storeList = res.data
				}
			} catch (e) {
				console.error('加載門店列表失敗', e)
				// 保持空數組，不使用模擬數據
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
			uni.showModal({ title: '提示', content: '您點擊了：' + name })
		},

		// ========== 首頁數據拉取 ==========
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
				console.error('加載首頁數據失敗', e)
				this.errorMsg = '首頁數據加載失敗，請確認後端服務是否已啟動'
				uni.showToast({ title: '首頁數據加載失敗', icon: 'none' })
			} finally {
				this.loading = false
			}
		},

		// 2.1 KPI 卡片：/api/dashboard/kpi（支持 store_id 篩選當前門店）
		async fetchKpiCards() {
			const store = getSelectedStore()
			const res = await apiGet('/dashboard/kpi', {
				params: store && store.store_id ? { store_id: store.store_id } : {}
			})
			if (!res || !res.success || !res.data) return

			const d = res.data
			// 映射為前端展示結構（可按需增減欄位）
			this.stats = [
				{
					label: 'SLA 達成率',
					value: `${d.sla_achievement_rate.value}${d.sla_achievement_rate.unit}`,
					sub: `較昨日 ${d.sla_achievement_rate.change}${d.sla_achievement_rate.unit}`,
					type: d.sla_achievement_rate.trend === 'up' ? 'normal' : 'low'
				},
				{
					label: '今日訂單數',
					value: `${d.today_orders.value}${d.today_orders.unit}`,
					sub: `較昨日 ${d.today_orders.change}${d.today_orders.unit}`,
					type: 'normal'
				},
				{
					label: '缺貨率',
					value: `${d.stockout_rate.value}${d.stockout_rate.unit}`,
					sub: `變化 ${d.stockout_rate.change}${d.stockout_rate.unit}`,
					// 缺貨率下降是好事
					type: d.stockout_rate.trend === 'down' ? 'normal' : 'low'
				},
				{
					label: '延遲配送次數',
					value: `${d.delivery_delay_count.value}${d.delivery_delay_count.unit}`,
					sub: `變化 ${d.delivery_delay_count.change}${d.delivery_delay_count.unit}`,
					type: d.delivery_delay_count.trend === 'down' ? 'normal' : 'low'
				}
			]
		},

		// 2.2 趨勢圖：/api/dashboard/trend（支持 store_id 篩選）
		async fetchTrendChart() {
			const store = getSelectedStore()
			const params = { metric: 'sla_rate', days: 7 }
			if (store && store.store_id) params.store_id = store.store_id
			const res = await apiGet('/dashboard/trend', { params })
			if (!res || !res.success || !res.data) return

			const trends = res.data.trends || []
			this.localChartData = {
				categories: trends.map(item => (item.date || '').slice(5)), // 顯示 MM-DD
				series: [
					{
						name: 'SLA 達成率',
						data: trends.map(item => item.value)
					}
				]
			}
		},

		// 2.3 實時預警摘要：/api/dashboard/alerts-summary
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
					critical: '嚴重'
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