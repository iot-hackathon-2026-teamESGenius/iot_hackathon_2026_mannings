<template>
	<view class="container">
		<AppNavBar title="订单管理" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 统计卡片 -->
			<view class="stats-section">
				<view class="stat-card">
					<text class="stat-value">{{ statistics.total_orders || 0 }}</text>
					<text class="stat-label">总订单数</text>
				</view>
				<view class="stat-card">
					<text class="stat-value">{{ statistics.completed_orders || 0 }}</text>
					<text class="stat-label">已完成</text>
				</view>
				<view class="stat-card">
					<text class="stat-value">{{ statistics.completion_rate || 0 }}%</text>
					<text class="stat-label">完成率</text>
				</view>
				<view class="stat-card">
					<text class="stat-value">{{ statistics.total_stores || 0 }}</text>
					<text class="stat-label">门店数</text>
				</view>
			</view>

			<!-- 筛选区 -->
			<view class="filter-card">
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">门店</text>
						<view class="store-selector" @click="openStoreModal">
							<text class="selector-text">{{ selectedStoreName || '全部门店' }}</text>
							<uni-icons type="bottom" size="14" color="#666"></uni-icons>
						</view>
					</view>
					<view class="filter-item half">
						<text class="label">日期范围</text>
						<uni-datetime-picker
							type="daterange"
							v-model="filters.dateRange"
							:border="true"
							@change="fetchOrders"
						/>
					</view>
				</view>
				<view class="filter-actions">
					<button class="btn-outline" size="mini" @click="resetFilters">重置</button>
					<button class="btn-primary" size="mini" @click="fetchOrders">搜索</button>
				</view>
			</view>

			<!-- 订单列表 -->
			<view class="section-title">订单列表</view>
			
			<view v-if="loading" class="hint">加载中...</view>
			<view v-else-if="errorMsg" class="hint error">{{ errorMsg }}</view>
			<template v-else>
				<view v-if="orders.length > 0" class="order-list">
					<view 
						v-for="(item, i) in orders" 
						:key="i"
						class="order-card"
						@click="showOrderDetail(item)"
					>
						<view class="order-header">
							<text class="order-id">{{ item.order_id }}</text>
							<text class="order-date">{{ item.order_date }}</text>
						</view>
						<view class="order-body">
							<view class="order-row">
								<text class="label">门店</text>
								<text class="value">{{ item.store_name || '门店' + item.store_code }}</text>
							</view>
							<view class="order-row">
								<text class="label">区域</text>
								<text class="value">{{ item.district || '-' }}</text>
							</view>
							<view class="order-row">
								<text class="label">订单数</text>
								<text class="value highlight">{{ item.total_orders }} 单</text>
							</view>
							<view class="order-row">
								<text class="label">商品数量</text>
								<text class="value">{{ item.total_quantity }} 件</text>
							</view>
						</view>
					</view>
				</view>
				<view v-else class="hint">暂无订单数据</view>
				
				<!-- 分页 -->
				<view v-if="totalPages > 1" class="pagination">
					<button 
						class="page-btn" 
						:disabled="currentPage <= 1"
						@click="prevPage"
					>上一页</button>
					<text class="page-info">{{ currentPage }} / {{ totalPages }}</text>
					<button 
						class="page-btn" 
						:disabled="currentPage >= totalPages"
						@click="nextPage"
					>下一页</button>
				</view>
			</template>

			<!-- 门店排行 -->
			<view class="section-title">门店订单排行 TOP 10</view>
			<view class="rank-list">
				<view 
					v-for="(store, i) in topStores" 
					:key="i"
					class="rank-item"
				>
					<view class="rank-num" :class="'rank-' + (i + 1)">{{ i + 1 }}</view>
					<view class="rank-info">
						<text class="rank-name">{{ store.store_name || '门店' + store.store_code }}</text>
						<text class="rank-detail">订单: {{ store.total_orders }} | 数量: {{ store.total_quantity }}</text>
					</view>
				</view>
			</view>

			<view style="height: 40rpx;"></view>
		</scroll-view>

		<!-- 门店选择弹窗 -->
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
						placeholder="搜索门店名称或ID"
					/>
				</view>
				<scroll-view scroll-y class="store-list">
					<view class="store-item" @click="selectAllStores">
						<text class="store-name">全部门店</text>
					</view>
					<view 
						v-for="store in filteredStores" 
						:key="store.store_id"
						class="store-item"
						@click="selectStore(store)"
					>
						<text class="store-name">{{ store.store_name }}</text>
						<text class="store-detail">ID: {{ store.store_id }}</text>
					</view>
				</scroll-view>
			</view>
		</view>

		<view class="tab-bar-placeholder"></view>
		<AppTabBar />
	</view>
</template>

<script>
import { apiGet } from '../../utils/api.js'
import AppNavBar from '../../components/app-nav-bar.vue'
import AppTabBar from '../../components/app-tab-bar.vue'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		return {
			// 统计数据
			statistics: {},
			topStores: [],
			
			// 订单列表
			orders: [],
			total: 0,
			currentPage: 1,
			pageSize: 20,
			totalPages: 1,
			
			// 筛选
			filters: {
				storeId: '',
				dateRange: ['', '']
			},
			selectedStoreName: '全部门店',
			
			// 门店选择
			showStoreModal: false,
			storeSearchText: '',
			storeOptions: [],
			
			loading: false,
			errorMsg: ''
		}
	},
	computed: {
		filteredStores() {
			if (!this.storeSearchText.trim()) {
				return this.storeOptions.slice(0, 50)
			}
			const search = this.storeSearchText.toLowerCase()
			return this.storeOptions.filter(s => 
				s.store_name?.toLowerCase().includes(search) ||
				String(s.store_id).includes(search)
			).slice(0, 50)
		}
	},
	onLoad() {
		this.loadStoreOptions()
		this.fetchStatistics()
		this.fetchOrders()
	},
	methods: {
		goBack() {
			uni.navigateBack()
		},
		
		async fetchStatistics() {
			try {
				const res = await apiGet('/orders/stats')
				if (res && res.success && res.data) {
					this.statistics = res.data
					this.topStores = res.data.top_stores || []
				}
			} catch (e) {
				console.error('获取统计失败', e)
			}
		},
		
		async fetchOrders() {
			this.loading = true
			this.errorMsg = ''
			try {
				const [date_from, date_to] = this.filters.dateRange || ['', '']
				const params = {
					page: this.currentPage,
					page_size: this.pageSize
				}
				if (this.filters.storeId) params.store_id = this.filters.storeId
				if (date_from) params.start_date = date_from
				if (date_to) params.end_date = date_to
				
				const res = await apiGet('/orders/list', { params })
				if (res && res.success && res.data) {
					this.orders = res.data.orders || []
					this.total = res.data.total || 0
					this.totalPages = res.data.total_pages || 1
				}
			} catch (e) {
				console.error('获取订单失败', e)
				this.errorMsg = '加载失败，请确认后端已启动'
			} finally {
				this.loading = false
			}
		},
		
		async loadStoreOptions() {
			try {
				const res = await apiGet('/auth/stores/public')
				if (res && res.success && res.data) {
					this.storeOptions = res.data
				}
			} catch (e) {
				console.error('加载门店列表失败', e)
			}
		},
		
		resetFilters() {
			this.filters = {
				storeId: '',
				dateRange: ['', '']
			}
			this.selectedStoreName = '全部门店'
			this.currentPage = 1
			this.fetchOrders()
		},
		
		prevPage() {
			if (this.currentPage > 1) {
				this.currentPage--
				this.fetchOrders()
			}
		},
		
		nextPage() {
			if (this.currentPage < this.totalPages) {
				this.currentPage++
				this.fetchOrders()
			}
		},
		
		// 门店选择
		openStoreModal() {
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
		},
		selectAllStores() {
			this.filters.storeId = ''
			this.selectedStoreName = '全部门店'
			this.closeStoreModal()
			this.currentPage = 1
			this.fetchOrders()
		},
		selectStore(store) {
			this.filters.storeId = store.store_id
			this.selectedStoreName = store.store_name
			this.closeStoreModal()
			this.currentPage = 1
			this.fetchOrders()
		},
		
		showOrderDetail(item) {
			uni.showModal({
				title: '订单详情',
				content: `订单ID: ${item.order_id}\n门店: ${item.store_name}\n订单数: ${item.total_orders}\n商品数量: ${item.total_quantity}`,
				showCancel: false
			})
		}
	}
}
</script>

<style lang="scss" scoped>
.container {
	background: #f4f7f9;
	min-height: 100vh;
}

.main-content {
	height: calc(100vh - 88rpx - var(--status-bar-height) - 100rpx);
	padding: 20rpx;
	box-sizing: border-box;
}

.tab-bar-placeholder {
	height: 120rpx;
}

/* 统计卡片 */
.stats-section {
	display: flex;
	gap: 16rpx;
	margin-bottom: 20rpx;
}

.stat-card {
	flex: 1;
	background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	border-radius: 16rpx;
	padding: 24rpx 16rpx;
	text-align: center;
	box-shadow: 0 4rpx 12rpx rgba(0, 102, 204, 0.2);
}

.stat-value {
	display: block;
	font-size: 36rpx;
	font-weight: bold;
	color: #fff;
}

.stat-label {
	display: block;
	font-size: 22rpx;
	color: rgba(255, 255, 255, 0.8);
	margin-top: 8rpx;
}

/* 筛选卡片 */
.filter-card {
	background: #fff;
	border-radius: 16rpx;
	padding: 24rpx;
	margin-bottom: 20rpx;
}

.filter-row {
	display: flex;
	gap: 20rpx;
	margin-bottom: 16rpx;
}

.filter-item {
	flex: 1;
	
	&.half {
		flex: 0 0 48%;
	}
	
	.label {
		display: block;
		font-size: 24rpx;
		color: #666;
		margin-bottom: 12rpx;
	}
}

.store-selector {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16rpx 20rpx;
	background: #f5f5f5;
	border-radius: 8rpx;
}

.selector-text {
	font-size: 28rpx;
	color: #333;
}

.filter-actions {
	display: flex;
	justify-content: flex-end;
	gap: 16rpx;
	margin-top: 16rpx;
}

/* 区块标题 */
.section-title {
	font-size: 30rpx;
	font-weight: bold;
	color: #333;
	margin: 24rpx 0 16rpx;
	padding-left: 16rpx;
	border-left: 6rpx solid #0066CC;
}

/* 订单列表 */
.order-list {
	display: flex;
	flex-direction: column;
	gap: 16rpx;
}

.order-card {
	background: #fff;
	border-radius: 16rpx;
	padding: 24rpx;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
}

.order-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16rpx;
	padding-bottom: 16rpx;
	border-bottom: 1rpx solid #eee;
}

.order-id {
	font-size: 26rpx;
	font-weight: bold;
	color: #0066CC;
}

.order-date {
	font-size: 24rpx;
	color: #999;
}

.order-body {
	display: flex;
	flex-wrap: wrap;
}

.order-row {
	width: 50%;
	display: flex;
	margin-bottom: 12rpx;
	
	.label {
		font-size: 24rpx;
		color: #999;
		width: 120rpx;
	}
	
	.value {
		font-size: 24rpx;
		color: #333;
		flex: 1;
		
		&.highlight {
			color: #0066CC;
			font-weight: bold;
		}
	}
}

/* 分页 */
.pagination {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 20rpx;
	margin-top: 24rpx;
}

.page-btn {
	padding: 12rpx 24rpx;
	font-size: 24rpx;
	background: #fff;
	border: 1rpx solid #ddd;
	border-radius: 8rpx;
	
	&:disabled {
		opacity: 0.5;
	}
}

.page-info {
	font-size: 24rpx;
	color: #666;
}

/* 排行榜 */
.rank-list {
	background: #fff;
	border-radius: 16rpx;
	overflow: hidden;
}

.rank-item {
	display: flex;
	align-items: center;
	padding: 20rpx 24rpx;
	border-bottom: 1rpx solid #f0f0f0;
	
	&:last-child {
		border-bottom: none;
	}
}

.rank-num {
	width: 48rpx;
	height: 48rpx;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24rpx;
	font-weight: bold;
	background: #f0f0f0;
	color: #666;
	margin-right: 20rpx;
	
	&.rank-1 {
		background: linear-gradient(135deg, #FFD700, #FFA500);
		color: #fff;
	}
	
	&.rank-2 {
		background: linear-gradient(135deg, #C0C0C0, #A0A0A0);
		color: #fff;
	}
	
	&.rank-3 {
		background: linear-gradient(135deg, #CD7F32, #B8860B);
		color: #fff;
	}
}

.rank-info {
	flex: 1;
}

.rank-name {
	display: block;
	font-size: 28rpx;
	color: #333;
	margin-bottom: 6rpx;
}

.rank-detail {
	display: block;
	font-size: 22rpx;
	color: #999;
}

/* 弹窗 */
.modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.5);
	z-index: 100;
	display: flex;
	align-items: center;
	justify-content: center;
}

.store-modal {
	width: 80%;
	max-height: 70vh;
	background: #fff;
	border-radius: 20rpx;
	overflow: hidden;
}

.modal-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 24rpx;
	border-bottom: 1rpx solid #eee;
}

.modal-title {
	font-size: 32rpx;
	font-weight: bold;
}

.search-box {
	padding: 20rpx 24rpx;
	border-bottom: 1rpx solid #eee;
}

.search-input {
	width: 100%;
	padding: 16rpx 20rpx;
	background: #f5f5f5;
	border-radius: 8rpx;
	font-size: 28rpx;
}

.store-list {
	max-height: 50vh;
}

.store-item {
	padding: 20rpx 24rpx;
	border-bottom: 1rpx solid #f0f0f0;
}

.store-name {
	display: block;
	font-size: 28rpx;
	color: #333;
}

.store-detail {
	display: block;
	font-size: 22rpx;
	color: #999;
	margin-top: 6rpx;
}

/* 按钮 */
.btn-primary {
	background: #0066CC;
	color: #fff;
}

.btn-outline {
	background: #fff;
	border: 1rpx solid #ddd;
	color: #666;
}

.hint {
	text-align: center;
	padding: 40rpx;
	color: #999;
	font-size: 28rpx;
	
	&.error {
		color: #dc3545;
	}
}
</style>
