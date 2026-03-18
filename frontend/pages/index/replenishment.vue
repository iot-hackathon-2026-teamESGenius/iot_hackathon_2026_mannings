<template>
	<view class="container">
		<AppNavBar title="补货计划" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 筛选区 -->
			<view class="filter-card">
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">补货日期范围</text>
						<uni-datetime-picker
							type="daterange"
							v-model="filters.dateRange"
							:border="true"
							@change="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">门店</text>
						<view class="store-selector" @click="openStoreModal">
							<text class="selector-text">{{ selectedStoreName || '全部门店' }}</text>
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
							placeholder="例如: DC01"
							@confirm="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">SKU ID</text>
						<input
							class="uni-input input-border"
							v-model="filters.skuId"
							placeholder="例如: SKU001"
							@confirm="fetchReplenishment"
						/>
					</view>
				</view>
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">状态</text>
						<uni-data-select
							v-model="filters.status"
							:localdata="statusOptions"
							placeholder="全部状态"
							@change="fetchReplenishment"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">ECDC ID</text>
						<input
							class="uni-input input-border"
							v-model="filters.ecdcId"
							placeholder="例如: ECDC01"
							@confirm="fetchReplenishment"
						/>
					</view>
				</view>
				<view class="filter-actions">
					<view class="left">
						<button class="btn-outline" size="mini" @click="resetFilters">重置</button>
					</view>
					<view class="right">
						<button class="btn-primary" size="mini" @click="fetchReplenishment">搜索</button>
					</view>
				</view>
			</view>

			<view v-if="loading" class="hint">加载中...</view>
			<view v-else-if="errorMsg" class="hint error">{{ errorMsg }}</view>
			<template v-else>
				<view v-if="statistics.total" class="stats-row">
					<text>共 {{ statistics.total }} 条</text>
					<text>待审 {{ statistics.pending }} · 已批准 {{ statistics.approved }} · 不可行 {{ statistics.infeasible }}</text>
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
						<text class="label">建议数量 / 补货日期</text>
						<text class="value">{{ item.recommended_qty }} / {{ item.replenishment_date }}</text>
					</view>
					<view v-if="item.actual_qty != null" class="card-row">
						<text class="label">实际数量</text>
						<text class="value">{{ item.actual_qty }}</text>
					</view>
					<view v-if="!item.is_feasible && item.infeasible_reason" class="reason">
					<text>不可行原因：{{ item.infeasible_reason }}</text>
				</view>
				<view class="card-actions" v-if="item.status === 'pending'">
					<button class="btn-action adjust-btn" size="mini" @click="openAdjustModal(item)">调整</button>
					<button class="btn-action approve-btn" size="mini" @click="openApproveModal(item)">审批</button>
				</view>
			</view>
			<view v-if="!plans.length" class="hint">暂无补货计划</view>
			</template>

			<!-- 调整弹窗 (自定义居中模态) -->
			<view v-if="adjustModalVisible" class="modal-overlay" @click.self="closeAdjustModal">
				<view class="modal-box" @click.stop>
					<view class="modal-header">调整补货数量</view>
					<view class="modal-body">
						<view class="modal-row">
							<text class="label">计划ID</text>
							<text class="value">{{ currentPlan?.plan_id }}</text>
						</view>
						<view class="modal-row">
							<text class="label">当前建议数量</text>
							<text class="value">{{ currentPlan?.recommended_qty }}</text>
						</view>
						<view class="modal-row">
							<text class="label">新数量</text>
							<input
								class="uni-input input-border"
								v-model.number="adjustment.new_qty"
								type="number"
								placeholder="请输入新的补货数量"
							/>
						</view>
						<view class="modal-row">
							<text class="label">调整原因</text>
							<textarea
								class="uni-textarea textarea-border"
								v-model="adjustment.reason"
								placeholder="请输入调整原因"
								rows="3"
							/>
						</view>
					</view>
					<view class="modal-footer">
						<button class="btn-action adjust-btn" @click="closeAdjustModal">取消</button>
						<button class="btn-action approve-btn" @click="confirmAdjust">确定</button>
					</view>
				</view>
			</view>

			<!-- 审批弹窗 (自定义居中模态) -->
			<view v-if="approveModalVisible" class="modal-overlay" @click.self="closeApproveModal">
				<view class="modal-box" @click.stop>
					<view class="modal-header">审批补货计划</view>
					<view class="modal-body">
						<view class="modal-row">
							<text class="label">计划ID</text>
							<text class="value">{{ currentPlan?.plan_id }}</text>
						</view>
						<view class="modal-row">
							<text class="label">审批结果</text>
							<view class="approval-radio">
								<radio-group v-model="approval.approved">
									<label>
										<radio :value="true" /> 批准
									</label>
									<label>
										<radio :value="false" /> 拒绝
									</label>
								</radio-group>
							</view>
						</view>
						<view class="modal-row" v-if="!approval.approved">
							<text class="label">拒绝原因</text>
							<textarea
								class="uni-textarea textarea-border"
								v-model="approval.reject_reason"
								placeholder="请输入拒绝原因"
								rows="3"
							/>
						</view>
					</view>
					<view class="modal-footer">
						<button class="btn-action adjust-btn" @click="closeApproveModal">取消</button>
						<button class="btn-action approve-btn" @click="confirmApprove">确定</button>
					</view>
				</view>
			</view>


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

		<AppTabBar />
	</view>
</template>

<script>
import AppNavBar from '../../components/app-nav-bar.vue'
import AppTabBar from '../../components/app-tab-bar.vue'
import { apiGet, apiPut, getUserInfo, getSelectedStore } from '../../utils/api.js'
import { canAccessPage } from '../../utils/permission.js'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		const today = new Date()
		const end = new Date()
		end.setDate(end.getDate() + 7)
		const format = (d) => d.toISOString().slice(0, 10)

		return {
			// 筛选条件
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
				{ value: '', text: '全部状态' },
				{ value: 'pending', text: '待审' },
				{ value: 'approved', text: '已批准' },
				{ value: 'rejected', text: '已拒绝' },
				{ value: 'adjusted', text: '已调整' }
			],
			plans: [],
			statistics: { total: 0, pending: 0, approved: 0, adjusted: 0, infeasible: 0 },
			loading: false,
			errorMsg: '',
			// 门店选择模态框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20, // 初始显示的门店数量
			// 调整与审批相关
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
		// 过滤后的门店列表（根据搜索文本）
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
		// 当前显示的门店列表（分页显示）
		displayedStores() {
			return this.filteredStoreList.slice(0, this.displayLimit)
		},
		// 是否还有更多门店
		hasMoreStores() {
			return this.filteredStoreList.length > this.displayLimit
		},
		// 当前选中门店的显示名称
		selectedStoreName() {
			if (!this.filters.storeId) return '全部门店'
			const store = this.storeOptions.find(s => s.store_id === this.filters.storeId)
			return store ? store.store_name : '全部门店'
		}
	},
	onLoad() {
		const userInfo = getUserInfo()
		if (!canAccessPage('/pages/index/replenishment', userInfo)) {
			uni.showToast({ title: '无访问权限', icon: 'none' })
			setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 800)
			return
		}
		// 默认使用首页当前选择的门店
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
			// 搜索输入处理，computed属性会自动更新filteredStoreList
			this.displayLimit = 20 // 重置显示限制
		},
		openStoreModal() {
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
			this.displayLimit = 20 // 重置显示限制
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
			this.displayLimit += 20 // 每次加载20个更多门店
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
				console.error('加载补货计划失败', e)
				this.errorMsg = '加载失败，请确认后端已启动'
				uni.showToast({ title: '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		async loadStoreOptions() {
			try {
				// 使用公开API获取门店列表
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回的原始格式，与首页保持一致
					this.storeOptions = res.data
				}
			} catch (e) {
				console.error('加载门店列表失败', e)
				// 保持空数组
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
				storeId: this.filters.storeId, // 保留当前门店
				dcId: '',
				ecdcId:'', // 保留门店作为 ECDC ID
				skuId: '',
				status: ''
			}
			this.fetchReplenishment()
		},
		statusText(s) {
			const map = { pending: '待审', approved: '已批准', adjusted: '已调整', rejected: '已拒绝' }
			return map[s] || s
		},
		// 调整相关方法
		openAdjustModal(plan) {
			if (!plan) return
			if (plan.status !== 'pending') {
				uni.showToast({ title: '只有待审计划可以调整', icon: 'none' })
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
				uni.showToast({ title: '新数量必须大于0', icon: 'none' })
				return
			}
			
			if (!this.adjustment.reason.trim()) {
				uni.showToast({ title: '请输入调整原因', icon: 'none' })
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
				// 标记为待审批状态以便界面立即反映
				uni.showToast({ title: '调整成功，已提交待审批', icon: 'success' })
				// 更新本地当前计划状态为 pending（待审）
				if (this.currentPlan) {
					this.currentPlan.status = 'pending'
					// 同步更新 plans 列表中的对应项
					const idx = this.plans.findIndex(p => p.plan_id === this.currentPlan.plan_id)
					if (idx !== -1) this.$set(this.plans, idx, Object.assign({}, this.plans[idx], { status: 'pending' }))
				}
				this.closeAdjustModal()
				// 如需从后端再次拉取最新数据，可保留下面一行；目前保留以确保服务器端状态一致
				this.fetchReplenishment()
			} catch (e) {
				console.error('调整补货计划失败', e)
				uni.showToast({ title: '调整失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		// 审批相关方法
		openApproveModal(plan) {
			if (!plan) return
			if (plan.status !== 'pending') {
				uni.showToast({ title: '只有待审计划可以审批', icon: 'none' })
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
				uni.showToast({ title: '请输入拒绝原因', icon: 'none' })
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
				uni.showToast({ title: '审批成功', icon: 'success' })
				this.closeApproveModal()
				this.fetchReplenishment()
			} catch (e) {
				console.error('审批补货计划失败', e)
				uni.showToast({ title: '审批失败', icon: 'none' })
			} finally {
				this.loading = false
			}
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
	padding: 0 30rpx;
	padding-bottom: 24rpx;
	box-sizing: border-box;
}
.tab-bar-placeholder {
	height: 120rpx;
}

/* 筛选卡片样式 */
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

/* 统计行样式 */
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

/* 卡片样式 */
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

/* 卡片操作按钮 */
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

.modal-content {
	background-color: #f9f9f9;
	max-width: 90%;
	  max-height: 90%;
	position: fixed;
	align-items: center;
	padding: 30rpx;
	max-width: 90vw;
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

/* 弹窗动画 */
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

/* 遮罩层样式 */
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

/* 响应式设计 */
@media screen and (max-width: 960px) {
	.filter-item.half {
		flex-basis: 100%;
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
