<template>
	<view class="container">
		<AppNavBar title="補貨計劃" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 筛选区 -->
			<view class="filter-card">
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">補貨日期範圍</text>
						<uni-datetime-picker
							type="daterange"
							v-model="filters.dateRange"
							:border="true"
							@change="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">門店</text>
						<view class="store-selector" @click="openStoreModal">
							<text class="selector-text">{{ selectedStoreName || '所有門店' }}</text>
							<uni-icons type="bottom" size="14" color="#666"></uni-icons>
						</view>
					</view>
				</view>
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">DC ID</text>
						<input
							class="uni-input input-border"
							v-model="filters.dcId"
							placeholder="例: DC01"
							@confirm="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">SKU ID</text>
						<input
							class="uni-input input-border"
							v-model="filters.skuId"
							placeholder="例: SKU001"
							@confirm="fetchReplenishment"
						/>
					</view>
				</view>
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">狀態</text>
						<uni-data-select
							v-model="filters.status"
							:localdata="statusOptions"
							placeholder="所有狀態"
							@change="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">ECDC ID</text>
						<input
							class="uni-input input-border"
							v-model="filters.ecdcId"
							placeholder="例: ECDC01"
							@confirm="fetchReplenishment"
						/>
					</view>
				</view>
				<view class="filter-actions">
					<view class="left">
						<button class="btn-outline" size="mini" @click="resetFilters">重設</button>
					</view>
					<view class="right">
						<button class="btn-primary" size="mini" @click="fetchReplenishment">搜尋</button>
					</view>
				</view>
			</view>

			<view v-if="loading" class="hint">載入中...</view>
			<view v-else-if="errorMsg" class="hint error">{{ errorMsg }}</view>
			<template v-else>
				<view v-if="statistics.total" class="stats-row">
					<text>共 {{ statistics.total }} 項</text>
					<text>待審 {{ statistics.pending }} · 已批准 {{ statistics.approved }} · 不可行 {{ statistics.infeasible }}</text>
				</view>
				<view
					v-for="(item, i) in plans"
					:key="item.plan_id || i"
					class="card"
					:class="{ infeasible: !item.is_feasible }"
				>
					<view class="card-head">
						<text class="plan-id">{{ item.plan_id }}</text>
						<text class="status-tag">{{ statusText(item.status) }}</text>
					</view>
					<view class="card-row">
						<text class="label">ECDC / SKU</text>
						<text class="value">{{ item.ecdc_name || item.ecdc_id }} · {{ item.sku_name || item.sku_id }}</text>
					</view>
					<view class="card-row">
						<text class="label">建議數量 / 補貨日期</text>
						<text class="value">{{ item.recommended_qty }} / {{ item.replenishment_date }}</text>
					</view>
					<view v-if="item.actual_qty != null" class="card-row">
						<text class="label">實際數量</text>
						<text class="value">{{ item.actual_qty }}</text>
					</view>
					<view v-if="!item.is_feasible && item.infeasible_reason" class="reason">
						<text>不可行原因：{{ item.infeasible_reason }}</text>
					</view>
					<view class="card-actions" v-if="item.status === 'pending'">
						<button class="btn-action adjust-btn" size="mini" @click="openAdjustModal(item)">調整</button>
						<button class="btn-action approve-btn" size="mini" @click="openApproveModal(item)">審批</button>
					</view>
				</view>
				<view v-if="!plans.length" class="hint">暫無補貨計劃</view>
			</template>

			<!-- 調整彈窗 -->
			<view v-if="adjustModalVisible" class="modal-overlay" @click.self="closeAdjustModal">
				<view class="modal-box" @click.stop>
					<view class="modal-header">調整補貨數量</view>
					<view class="modal-body">
						<view class="modal-row">
							<text class="label">計劃 ID</text>
							<text class="value">{{ currentPlan?.plan_id }}</text>
						</view>
						<view class="modal-row">
							<text class="label">當前建議數量</text>
							<text class="value">{{ currentPlan?.recommended_qty }}</text>
						</view>
						<view class="modal-row">
							<text class="label">新數量</text>
							<input
								class="uni-input input-border"
								v-model.number="adjustment.new_qty"
								type="number"
								placeholder="輸入新補貨數量"
							/>
						</view>
						<view class="modal-row">
							<text class="label">調整原因</text>
							<textarea
								class="uni-textarea textarea-border"
								v-model="adjustment.reason"
								placeholder="輸入調整原因"
								rows="3"
							/>
						</view>
					</view>
					<view class="modal-footer">
						<button class="btn-action adjust-btn" @click="closeAdjustModal">取消</button>
						<button class="btn-action approve-btn" @click="confirmAdjust">確認</button>
					</view>
				</view>
			</view>

			<!-- 審批彈窗 -->
			<view v-if="approveModalVisible" class="modal-overlay" @click.self="closeApproveModal">
				<view class="modal-box" @click.stop>
					<view class="modal-header">審批補貨計劃</view>
					<view class="modal-body">
						<view class="modal-row">
							<text class="label">計劃 ID</text>
							<text class="value">{{ currentPlan?.plan_id }}</text>
						</view>
						<view class="modal-row">
							<text class="label">審批結果</text>
							<view class="approval-radio">
								<radio-group  :value="approval.approved ">
									<label>
										<radio :value="true" /> 批准
									</label>
									<label>
										<radio :value="false" /> 拒絕
									</label>
								</radio-group>
							</view>
						</view>
						<view class="modal-row" v-if="!approval.approved">
							<text class="label">拒絕原因</text>
							<textarea
								class="uni-textarea textarea-border"
								v-model="approval.reject_reason"
								placeholder="輸入拒絕原因"
								rows="3"
							/>
						</view>
					</view>
					<view class="modal-footer">
						<button class="btn-action adjust-btn" @click="closeApproveModal">取消</button>
						<button class="btn-action approve-btn" @click="confirmApprove">確認</button>
					</view>
				</view>
			</view>

		</scroll-view>

		<!-- 門店選擇模態框 -->
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
							<text class="store-name">所有門店</text>
							<text class="store-detail">顯示所有門店數據</text>
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
						<text>未找到匹配門店</text>
					</view>
					<view v-if="hasMoreStores" class="load-more" @click="loadMoreStores">
						<text>載入更多 ({{ filteredStoreList.length - displayedStores.length }} 個)</text>
					</view>
				</scroll-view>
			</view>
		</view>

<!-- 		<AppTabBar /> -->
	</view>
</template>

<script>
import AppNavBar from '../../components/app-nav-bar.vue'
import { apiGet, apiPut, getUserInfo, getSelectedStore } from '../../utils/api.js'
import { canAccessPage } from '../../utils/permission.js'

export default {
	components: { AppNavBar },
	data() {
		const today = new Date()
		const end = new Date()
		end.setDate(end.getDate() + 7)
		const format = (d) => d.toISOString().slice(0, 10)

		return {
			// 篩選條件
			filters: {
				dateRange: [format(today), format(end)],
				storeId: '',
				dcId: '',
				ecdcId: '',
				skuId: '',
				status: ''
			},
			storeOptions: [],
			statusOptions: [
				{ value: '', text: '所有狀態' },
				{ value: 'pending', text: '待審' },
				{ value: 'approved', text: '已批准' },
				{ value: 'rejected', text: '已拒絕' },
				{ value: 'adjusted', text: '已調整' }
			],
			plans: [],
			statistics: { total: 0, pending: 0, approved: 0, adjusted: 0, infeasible: 0 },
			loading: false,
			errorMsg: '',
			// 門店選擇模態框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20, // 初始顯示門店數量
			// 調整與審批相關
			adjustModalVisible: false,
			approveModalVisible: false,
			currentPlan: null,
			adjustment: {
				new_qty: 0,
				reason: ''
			},
			approval: {
				approved: true,
				reject_reason: ''
			}
		}
	},
	computed: {
		// 過濾後門店列表（根據搜尋文本）
		filteredStoreList() {
			if (!this.storeSearchText.trim()) {
				return this.storeOptions
			}
			const searchText = this.storeSearchText.toLowerCase()
			return this.storeOptions.filter(store => {
				return store.store_name.toLowerCase().includes(searchText) ||
					   store.store_id.toLowerCase().includes(searchText) ||
					   (store.district && store.district.toLowerCase().includes(searchText))
			})
		},
		// 當前顯示門店列表（分頁顯示）
		displayedStores() {
			return this.filteredStoreList.slice(0, this.displayLimit)
		},
		// 是否還有更多門店
		hasMoreStores() {
			return this.filteredStoreList.length > this.displayLimit
		},
		// 當前選中門店顯示名稱
		selectedStoreName() {
			if (!this.filters.storeId) return '所有門店'
			const store = this.storeOptions.find(s => s.store_id === this.filters.storeId)
			return store ? store.store_name : '所有門店'
		}
	},
	onLoad() {
		const userInfo = getUserInfo()
		if (!canAccessPage('/pages/index/replenishment', userInfo)) {
			uni.showToast({ title: '無訪問權限', icon: 'none' })
			setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 800)
			return
		}
		// 默認使用首頁當前選擇門店
		const selected = getSelectedStore && getSelectedStore()
		if (selected && selected.store_id) {
			this.filters.storeId = selected.store_id
		}
		this.loadStoreOptions()
		this.fetchReplenishment()
	},
	methods: {
		goBack() {
			uni.navigateBack()
		},
		onStoreSearch() {
			// 搜尋輸入處理
			this.displayLimit = 20 // 重設顯示限制
		},
		openStoreModal() {
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
			this.displayLimit = 20 // 重設顯示限制
		},
		selectStore(store) {
			this.filters.storeId = store.store_id
			this.closeStoreModal()
			this.fetchReplenishment()
		},
		selectAllStores() {
			this.filters.storeId = ''
			this.closeStoreModal()
			this.fetchReplenishment()
		},
		loadMoreStores() {
			this.displayLimit += 20 // 每次載入20個更多門店
		},
		async fetchReplenishment() {
			this.loading = true
			this.errorMsg = ''
			try {
				const [date_from, date_to] = this.filters.dateRange || ['', '']
				const params = {
					date_from,
					date_to,
					dc_id: this.filters.dcId,
					ecdc_id: this.filters.ecdcId,
					sku_id: this.filters.skuId,
					status: this.filters.status
				}
				if (this.filters.storeId) params.store_id = this.filters.storeId
				const res = await apiGet('/planning/replenishment', { params })
				if (res && res.success && res.data) {
					this.plans = res.data.plans || []
					this.statistics = res.data.statistics || this.statistics
				}
			} catch (e) {
				console.error('載入補貨計劃失敗', e)
				this.errorMsg = '載入失敗，請確認後端已啟動'
				uni.showToast({ title: '載入失敗', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		async loadStoreOptions() {
			try {
				// 使用公開API獲取門店列表
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回原始格式
					this.storeOptions = res.data
				}
			} catch (e) {
				console.error('載入門店列表失敗', e)
				// 保持空數組
				this.storeOptions = []
			}
		},
		resetFilters() {
			const today = new Date()
			const end = new Date()
			end.setDate(end.getDate() + 7)
			const format = (d) => d.toISOString().slice(0, 10)
			
			this.filters = {
				dateRange: [format(today), format(end)],
				storeId: this.filters.storeId, // 保留當前門店
				dcId: '',
				ecdcId:'', // 保留門店作為 ECDC ID
				skuId: '',
				status: ''
			}
			this.fetchReplenishment()
		},
		statusText(s) {
			const map = { pending: '待審', approved: '已批准', adjusted: '已調整', rejected: '已拒絕' }
			return map[s] || s
		},
		// 調整相關方法
		openAdjustModal(plan) {
			if (!plan) return
			if (plan.status !== 'pending') {
				uni.showToast({ title: '只有待審計劃可以調整', icon: 'none' })
				return
			}
			this.currentPlan = plan
			this.adjustment = {
				new_qty: plan.recommended_qty,
				reason: ''
			}
			this.adjustModalVisible = true
		},
		closeAdjustModal() {
			this.adjustModalVisible = false
			this.currentPlan = null
			this.adjustment = {
				new_qty: 0,
				reason: ''
			}
		},
		async confirmAdjust() {
			if (!this.currentPlan) return
			
			if (this.adjustment.new_qty <= 0) {
				uni.showToast({ title: '新數量必須大於0', icon: 'none' })
				return
			}
			
			if (!this.adjustment.reason.trim()) {
				uni.showToast({ title: '請輸入調整原因', icon: 'none' })
				return
			}
			
			this.loading = true
			try {
				const data = {
					new_qty: this.adjustment.new_qty,
					reason: this.adjustment.reason,
					operator: 'system'
				}
				await apiPut(`/planning/replenishment/${this.currentPlan.plan_id}/adjust`, data)
				// 標記為待審批狀態以便界面立即反映
				uni.showToast({ title: '調整成功，已提交待審批', icon: 'success' })
				// 更新本地當前計劃狀態為 pending（待審）
				if (this.currentPlan) {
					this.currentPlan.status = 'pending'
					// 同步更新 plans 列表中對應項
					const idx = this.plans.findIndex(p => p.plan_id === this.currentPlan.plan_id)
					if (idx !== -1) this.$set(this.plans, idx, Object.assign({}, this.plans[idx], { status: 'pending' }))
				}
				this.closeAdjustModal()
				// 如需從後端再次拉取最新數據，可保留下面一行
				this.fetchReplenishment()
			} catch (e) {
				console.error('調整補貨計劃失敗', e)
				uni.showToast({ title: '調整失敗', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		// 審批相關方法
		openApproveModal(plan) {
			if (!plan) return
			if (plan.status !== 'pending') {
				uni.showToast({ title: '只有待審計劃可以審批', icon: 'none' })
				return
			}
			this.currentPlan = plan
			this.approval = {
				approved: true,
				reject_reason: ''
			}
			this.approveModalVisible = true
		},
		closeApproveModal() {
			this.approveModalVisible = false
			this.currentPlan = null
			this.approval = {
				approved: true,
				reject_reason: ''
			}
		},
		async confirmApprove() {
			if (!this.currentPlan) return
			
			if (!this.approval.approved && !this.approval.reject_reason.trim()) {
				uni.showToast({ title: '請輸入拒絕原因', icon: 'none' })
				return
			}
			
			this.loading = true
			try {
				const data = {
					approved: this.approval.approved,
					reviewer: 'system',
					reject_reason: this.approval.reject_reason
				}
				await apiPut(`/planning/replenishment/${this.currentPlan.plan_id}/approve`, data)
				uni.showToast({ title: '審批成功', icon: 'success' })
				this.closeApproveModal()
				this.fetchReplenishment()
			} catch (e) {
				console.error('審批補貨計劃失敗', e)
				uni.showToast({ title: '審批失敗', icon: 'none' })
			} finally {
				this.loading = false
			}
		}
	}
}
</script>

<style lang="scss" scoped>
/* 樣式保持不變，僅修改文字部分 */
.container {
	background: #f4f7f9;
	min-height: 100vh;
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

/* 篩選卡片樣式 */
.filter-card {
	background: #fff;
	border-radius: 16rpx;
	padding: 20rpx 24rpx 16rpx;
	margin-top: 24rpx;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.03);
}
.filter-row {
	display: flex;
	flex-wrap: wrap;
	gap: 16rpx;
	margin-bottom: 12rpx;
}
.filter-item {
	flex: 1 1 100%;
	.label {
		display: block;
		font-size: 26rpx;
		color: #666;
		margin-bottom: 8rpx;
	}
}
.filter-item.half {
	flex-basis: calc(50% - 8rpx);
}
.store-selector {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10rpx 14rpx;
	border: 1px solid #ddd;
	border-radius: 8rpx;
	background-color: #fff;
	cursor: pointer;
	
	.selector-text {
		font-size: 26rpx;
		color: #333;
	}
}
.input-border {
	border: 1px solid #ddd;
	padding: 10rpx 14rpx;
	border-radius: 8rpx;
	font-size: 26rpx;
	background-color: #fff;
}
.textarea-border {
	border: 1px solid #ddd;
	padding: 10rpx 14rpx;
	border-radius: 8rpx;
	font-size: 26rpx;
	background-color: #fff;
	height: 120rpx;
}
.filter-actions {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-top: 8rpx;
	.left {
		button {
			border: 1px solid #ccc;
			font-size: 24rpx;
			padding: 0 20rpx;
		}
	}
	.right {
		display: flex;
		align-items: center;
		gap: 12rpx;
	}
	.btn-outline {
		background: #fff;
		color: #666;
		border-radius: 999rpx;
		font-size: 24rpx;
		height: 60rpx;
		line-height: 60rpx;
	}
	.btn-primary {
		background: #0066CC;
		color: #fff;
		font-size: 24rpx;
		padding: 0 24rpx;
		border-radius: 999rpx;
		height: 60rpx;
		line-height: 60rpx;
	}
}

/* 統計行樣式 */
.stats-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 20rpx 24rpx;
	background: #fff;
	border-radius: 16rpx;
	margin-bottom: 24rpx;
	margin-top: 24rpx;
	font-size: 26rpx;
	color: #666;
}

/* 卡片樣式 */
.card {
	background: #fff;
	border-radius: 20rpx;
	padding: 28rpx 24rpx;
	margin-bottom: 24rpx;
	box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.06);
	&.infeasible { border-left: 6rpx solid #FD7E14; }
}
.card-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16rpx;
}
.plan-id { font-size: 26rpx; color: #333; }
.status-tag {
	font-size: 22rpx;
	padding: 6rpx 14rpx;
	border-radius: 20rpx;
	background: #e8f4fd;
	color: #0066CC;
}
.card-row {
	display: flex;
	justify-content: space-between;
	margin-bottom: 12rpx;
	font-size: 26rpx;
}
.label { color: #888; }
.value { color: #333; }
.reason {
	margin-top: 12rpx;
	padding-top: 12rpx;
	border-top: 1px dashed #fee2e2;
	font-size: 26rpx;
	color: #DC3545;
}

/* 卡片操作按鈕 */
.card-actions {
	display: flex;
	gap: 12rpx;
	margin-top: 20rpx;
	padding-top: 16rpx;
	border-top: 1px solid #f0f0f0;
}
.btn-action {
	flex: 1;
	font-size: 24rpx;
	padding: 8rpx 0;
	border-radius: 8rpx;
	height: 60rpx;
	line-height: 60rpx;
}
.adjust-btn {
	background: #FFC107;
	color: #333;
}
.approve-btn {
	background: #28a745;
	color: #fff;
}

.modal-overlay {
	position: fixed;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(0,0,0,0.45);
	z-index: 2000;
	padding: 24rpx;
}
.modal-box {
	width: 740rpx;
	max-width: 100%;
	background: #ffffff;
	border-radius: 20rpx;
	box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.12);
	overflow: hidden;
	animation: modalFadeIn 180ms ease-out;
}
.modal-header {
	padding: 28rpx 32rpx;
	font-size: 30rpx;
	font-weight: 600;
	color: #212529;
	border-bottom: 1px solid #f0f0f0;
}
.modal-body {
	padding: 26rpx 32rpx;
	background: #fff;
}
.modal-footer {
	display: flex;
	gap: 18rpx;
	padding: 18rpx 22rpx 28rpx;
	justify-content: flex-end;
	background: #fff;
	border-top: 1px solid #f6f6f6;
}
.modal-footer .btn-action {
	min-width: 160rpx;
}
.modal-row {
	margin-bottom: 24rpx;
	.label {
		display: block;
		font-size: 26rpx;
		color: #555;
		margin-bottom: 10rpx;
		font-weight: 500;
	}
	.value {
		font-size: 26rpx;
		color: #333;
		font-weight: bold;
	}
}
.approval-radio {
	label {
		display: block;
		margin-bottom: 16rpx;
		font-size: 26rpx;
		color: #333;
	}
	radio {
		margin-right: 12rpx;
		transform: scale(1.2);
	}
}

/* 彈窗動畫 */
@keyframes modalFadeIn {
	from {
		opacity: 0;
		transform: scale(0.9) translateY(-20rpx);
	}
	to {
		opacity: 1;
		transform: scale(1) translateY(0);
	}
}

/* 遮罩層樣式 */
:deep(.uni-modal__mask) {
	background: rgba(0, 0, 0, 0.5);
	animation: maskFadeIn 0.3s ease-out;
}

@keyframes maskFadeIn {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}

/* 提示信息 */
.hint {
	text-align: center;
	padding: 60rpx 24rpx;
	font-size: 28rpx;
	color: #666;
	&.error { color: #DC3545; }
}

/* 響應式設計 */
@media screen and (max-width: 960px) {
	.filter-item.half {
		flex-basis: 100%;
	}
}

/* 門店選擇模態框樣式 */
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