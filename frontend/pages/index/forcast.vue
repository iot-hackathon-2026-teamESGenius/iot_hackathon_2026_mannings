<template>
	<view class="container">
		<AppNavBar title="需求預測" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 篩選區 -->
			<view class="filter-card">
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">預測日期範圍</text>
						<uni-datetime-picker
							type="daterange"
							v-model="filters.dateRange"
							:border="true"
							@change="onDateChange"
						/>
					</view>
					<view class="filter-item half">
						<text class="label">門店</text>
						<view class="store-selector" @click="openStoreModal">
							<text class="selector-text">{{ selectedStoreName || '全部門店' }}</text>
							<uni-icons type="bottom" size="14" color="#666"></uni-icons>
						</view>
					</view>
				</view>

				<view class="filter-row">
					<view class="filter-item two-thirds">
						<text class="label">SKU ID 列表</text>
						<view class="sku-search">
							<input
								class="uni-input input-border"
								v-model="filters.skuIds"
								placeholder="例如: SKU001,SKU002（必填）"
								@confirm="fetchForecast"
							/>
							<button class="btn-mini" size="mini" @click="applyFilters">搜尋</button>
						</view>
					</view>
					<view class="filter-item one-third" v-if="displayMode !== 'chart'">
						<text class="label">庫存狀態</text>
						<view class="status-tabs">
							<text
								v-for="s in statusOptions"
								:key="s.value"
								class="status-tab"
								:class="{ active: filters.status === s.value, [s.value]: s.value }"
								@click="changeStatus(s.value)"
							>
								{{ s.text }}
							</text>
						</view>
					</view>
				</view>

				<view class="filter-actions">
					<view class="left">
						<button class="btn-outline" size="mini" @click="resetFilters">重置</button>
					</view>
					<view class="right">
						<button
							class="btn-toggle"
							size="mini"
							:class="{ active: displayMode === 'list' }"
							@click="displayMode = 'list'"
						>
							列表
						</button>
							<button
							class="btn-toggle"
							size="mini"
							:class="{ active: displayMode === 'chart' }"
							@click="displayMode = 'chart'"
						>
							圖表
						</button>
						<button class="btn-primary" size="mini" @click="exportReport">導出報表</button>
					</view>
				</view>
			</view>

			<!-- 加載與錯誤提示 -->
			<view v-if="loading" class="hint">加載中...</view>
			<view v-else-if="errorMsg" class="hint error">{{ errorMsg }}</view>

			<!-- 圖表模式 -->
			<view v-else-if="displayMode === 'chart'">
				<uni-section title="需求趨勢" type="line" padding>
					<view class="chart-box">
									<div class="chart-inner" :style="{ minWidth: chartInnerWidth + 'px' }">
										<qiun-data-charts
											type="mix"
											:opts="mixChartOpts"
											:chartData="mixChartData"
											:canvas2d="true"
										/>
									</div>
					</view>
				</uni-section>
			</view>

			<!-- 列表模式 -->
			<template v-else>
				<view class="stats-row" v-if="filteredForecasts.length">
					<text>共 {{ filteredForecasts.length }} 條 · 需求合計 {{ totalForecast }} 件</text>
				</view>

				<view class="table-wrapper" v-if="filteredForecasts.length">
					<view class="table-header">
						<text class="col store">門店</text>
						<text class="col sku">SKU</text>
						<text class="col date">日期</text>
						<text class="col qty" @click="toggleSort">預測量▼</text>
						<text class="col status">狀態</text>
					</view>
					<view
						class="table-row"
						v-for="(item, i) in sortedForecasts"
						:key="i"
					>
						<text class="col store">
							{{ item.store_name || item.store_id }}
						</text>
						<view class="col sku sku-cell">
							<text class="sku-id">{{ item.sku_id }}</text>
							<text class="sku-name">{{ item.sku_name }}</text>
						</view>
						<text class="col date">{{ item.date }}</text>
						<text class="col qty">{{ item.forecast_demand }}</text>
						<view class="col status">
							<view class="status-pill" :class="item._stock_status">
								<uni-icons
									v-if="item._stock_status === 'shortage'"
									type="info-filled"
									size="14"
									color="#DC3545"
								/>
								<uni-icons
									v-else-if="item._stock_status === 'overstock'"
									type="info-filled"
									size="14"
									color="#FD7E14"
								/>
								<text>{{ statusText(item._stock_status) }}</text>
							</view>
						</view>
					</view>
				</view>

				<view v-if="!filteredForecasts.length && !loading && !errorMsg" class="hint">
					暫無需求預測數據
				</view>
			</template>

			<view class="tab-bar-placeholder"></view>
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
						<text>加載更多 ({{ filteredStoreList.length - displayedStores.length }} 個)</text>
					</view>
				</scroll-view>
			</view>
		</view>
	</view>
</template>

<script>
import AppNavBar from '../../components/app-nav-bar.vue'

import { apiGet, getSelectedStore } from '../../utils/api.js'

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
				skuIds: 'SKU001', // 默認商品 SKU001
				status: 'all' // all / normal / shortage / overstock
			},
			storeOptions: [],
			statusOptions: [
				{ value: 'all', text: '全部' },
				{ value: 'normal', text: '正常' },
				{ value: 'shortage', text: '缺貨' },
				{ value: 'overstock', text: '積壓' }
			],

			// 原始數據與過濾後數據
			forecasts: [],

			// 圖表數據（混合：預測折線 + 實際柱狀）
			mixChartData: { categories: [], series: [] },
			// 嘗試這種方式
			mixChartOpts: {
			  // 圖表標題配置
			  title: {
			    name: '需求趨勢',
			    fontSize: 16,
			    color: '#333333',
			    padding: [20, 0, 0, 0]  // 上右下左
			  },
			  
			  xAxis: {
			    disableGrid: false,
			    gridColor: '#F0F0F0',
			    fontSize: 12,
			    fontColor: '#666666',
			    boundaryGap: 'justify',
			    labelCount: 7
			  },
			  
			  yAxis: {
			    gridType: 'dash',
			    dashLength: 4,
			    gridColor: '#F0F0F0',
			    splitNumber: 5,
			    
			    // 添加軸標題
			    title: {
			      name: '數量(件)',
			      fontSize: 12,
			      color: '#666666',
			      offsetX: -10
			    },
			    
			    data: [{
			      position: 'left',
			      min: 0,
			      fontSize: 12,
			      fontColor: '#666666',
			      axisLine: true,
			      axisLineColor: '#CCCCCC',
			      axisLineWidth: 1
			    }]
			  }
			},
			// 動態計算圖表內部寬度（用於橫向滾動）
			chartInnerWidth: 600,

			// UI 狀態
			loading: false,
			errorMsg: '',
			displayMode: 'chart', // 默認以圖表展示
			sortDesc: true,
			// 門店選擇模態框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20 // 初始顯示的門店數量
		}
	},
	computed: {
		// 按篩選條件得到的列表
		filteredForecasts() {
			let list = this.forecasts.slice()
			if (this.filters.status !== 'all') {
				list = list.filter((i) => i._stock_status === this.filters.status)
			}
			return list
		},
		// 排序後的列表（按預測量）
		sortedForecasts() {
			const list = this.filteredForecasts.slice()
			list.sort((a, b) =>
				this.sortDesc
					? b.forecast_demand - a.forecast_demand
					: a.forecast_demand - b.forecast_demand
			)
			return list
		},
		totalForecast() {
			return this.filteredForecasts
				.reduce((sum, i) => sum + (i.forecast_demand || 0), 0)
				.toFixed(1)
		},
		// 過濾後的門店列表（根據搜尋文本）
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
		// 當前顯示的門店列表（分頁顯示）
		displayedStores() {
			return this.filteredStoreList.slice(0, this.displayLimit)
		},
		// 是否還有更多門店
		hasMoreStores() {
			return this.filteredStoreList.length > this.displayLimit
		},
		// 當前選中門店的顯示名稱
		selectedStoreName() {
			if (!this.filters.storeId) return '全部門店'
			const store = this.storeOptions.find(s => s.store_id === this.filters.storeId)
			return store ? store.store_name : '全部門店'
		}
	},
	onLoad() {
		// 默認使用首頁當前選擇的門店
		const selected = getSelectedStore && getSelectedStore()
		if (selected && selected.store_id) {
			this.filters.storeId = selected.store_id
		}
		this.displayMode = 'chart'
		this.loadStoreOptions()
		this.fetchForecast()
	},
	methods: {
		goBack() {
			uni.navigateBack()
		},
		onStoreSearch() {
			// 搜尋輸入處理，computed屬性會自動更新filteredStoreList
			this.displayLimit = 20 // 重置顯示限制
		},
		openStoreModal() {
			this.showStoreModal = true
		},
		closeStoreModal() {
			this.showStoreModal = false
			this.storeSearchText = ''
			this.displayLimit = 20 // 重置顯示限制
		},
		selectStore(store) {
			this.filters.storeId = store.store_id
			this.closeStoreModal()
			this.fetchForecast()
		},
		selectAllStores() {
			this.filters.storeId = ''
			this.closeStoreModal()
			this.fetchForecast()
		},
		loadMoreStores() {
			this.displayLimit += 20 // 每次加載20個更多門店
		},
		onDateChange() {
			this.fetchForecast()
		},
		changeStatus(v) {
			this.filters.status = v
		},
		resetFilters() {
			this.filters.skuIds = ''
			this.filters.status = 'all'
			// 保留當前門店，只重置 SKU/狀態
			this.fetchForecast()
		},
		applyFilters() {
			this.fetchForecast()
		},
		toggleSort() {
			this.sortDesc = !this.sortDesc
		},
		statusText(s) {
			const map = {
				normal: '正常',
				shortage: '缺貨',
				overstock: '積壓'
			}
			return map[s] || s || '正常'
		},
		async fetchForecast() {
			const [start, end] = this.filters.dateRange || []
			if (!start || !end) {
				uni.showToast({ title: '請先選擇日期範圍', icon: 'none' })
				return
			}
			if (!this.filters.storeId) {
				uni.showToast({ title: '請選擇門店', icon: 'none' })
				return
			}
			if (!this.filters.skuIds || !this.filters.skuIds.trim()) {
				uni.showToast({ title: '請輸入 SKU ID 列表', icon: 'none' })
				return
			}
			this.loading = true
			this.errorMsg = ''
			try {
				const params = {
					start_date: start,
					end_date: end,
					page: 1,
					page_size: 200
				}
				if (this.filters.storeId) {
					params.store_ids = this.filters.storeId
				}
				// SKU ID 列表，逗號分隔
				params.sku_ids = this.filters.skuIds
				const res = await apiGet('/forecast/demand', { params })
				if (res && res.success && res.data && res.data.forecasts) {
					const list = res.data.forecasts.map((f) => {
						const status = this.computeStatus(f)
						return { ...f, _stock_status: status }
					})
					this.forecasts = list
					this.buildCharts()
				} else {
					this.forecasts = []
					this.mixChartData = { categories: [], series: [] }
				}
			} catch (e) {
				console.error('獲取需求預測失敗', e)
				this.errorMsg = '加載失敗，請確認後端已啟動'
				uni.showToast({ title: '加載失敗', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		// 通過預測值與上下界粗略推斷庫存狀態
		computeStatus(item) {
			const p = Number(item.forecast_demand || 0)
			const low = Number(item.lower_bound || 0)
			const up = Number(item.upper_bound || 0)
			if (p < low) return 'shortage'
			if (p > up) return 'overstock'
			return 'normal'
		},
		buildCharts() {
            const list = this.filteredForecasts
            if (!list.length) {
                this.mixChartData = { title: { name: '需求預測' }, categories: [], series: [] }
                this.mixChartOpts.title.name = '需求預測'
                return
            }
            // 維度：日期 + SKU
            const dateSet = new Set()
            const skuSet = new Set()
            list.forEach((i) => {
                if (i.date) dateSet.add(i.date)
                if (i.sku_id) skuSet.add(i.sku_id)
            })
            const dates = Array.from(dateSet).sort()
            // 橫坐標顯示去掉年份，只保留 MM-DD
            const displayDates = dates.map(d => (typeof d === 'string' && d.length >= 5) ? d.slice(5) : d)
            let skus = Array.from(skuSet)
            // 如果沒有檢測到 SKU，則使用 filters.skuIds（可能為逗號分隔）或回退到默認 SKU001
            if (!skus.length) {
                if (this.filters.skuIds && this.filters.skuIds.trim()) {
                    skus = this.filters.skuIds.split(',').map(s => s.trim()).filter(Boolean)
                }
                if (!skus.length) skus = ['SKU001']
            }

            const series = []
            skus.forEach((skuId) => {
                const forecastArr = []
                const actualArr = []
                dates.forEach((d) => {
                    const items = list.filter((i) => i.sku_id === skuId && i.date === d)
                    const fSum = items.reduce((s, it) => s + (it.forecast_demand || 0), 0)
                    const aSum = items.reduce((s, it) => s + (it.actual_demand || 0), 0)
                    forecastArr.push(Number(fSum.toFixed(1)))
                    actualArr.push(Number(aSum.toFixed(1)))
                })
                // 預測：折線，顏色 & 標籤在上方
                series.push({
                    name: `${skuId || 'SKU001'} 預測`,
                    type: 'line',
                    data: forecastArr,
                    itemStyle: { color: '#FF7F50' }, // 橙色
                    label: { show: true, color: '#FF7F50', position: 'top' },
                    smooth: true
                })
                // 實際：柱狀，顏色與標籤位置不同，標籤放在柱內避免與折線標籤遮擋
                series.push({
                    name: `${skuId || 'SKU001'} 實際`,
                    type: 'column',
                    data: actualArr,
                    itemStyle: { color: '#2F90FF' }, // 藍色柱子
                    label: { show: true, color: '#ffffff', position: 'inside' }, // 白色字體在柱內
                    barGap: '30%'
                })
            })

            // 計算標題：單 SKU 使用 sku_name（優先）或 skuId，否則回退到默認
            let chartTitle = '需求趨勢'
			
            if (skus.length === 1) {
                const skuIdPrimary = skus[0]
                const skuNameItem = this.forecasts.find(i => i.sku_id === skuIdPrimary && i.sku_name)
                const skuLabel = (skuNameItem && skuNameItem.sku_name) ? skuNameItem.sku_name : (skuIdPrimary || 'SKU001')
                chartTitle = `${skuLabel} 需求趨勢`
            } else {
                chartTitle = '需求趨勢'
            }
            // 如果有門店篩選，加入門店名前綴（可選）
            if (this.filters.storeId) {
                const store = this.storeOptions.find(s => s.value === this.filters.storeId)
                if (store && store.text) {
                    chartTitle = `${store.text} ${chartTitle}`
                }
            }

            // 把標題寫入 opts 和 data（組件可能從不同位置讀取）
            this.mixChartOpts.title.name = chartTitle
            // mixChartData.title 使用對象形式，避免字符串->對象訪問導致 undefined
            this.mixChartData = {
                title: { name: chartTitle },
                categories: displayDates,
                series
            }

            // 給 x/y 軸添加 name（如果需要顯示軸標題）
            this.mixChartOpts.xAxis.name = '日期'
            this.mixChartOpts.yAxis.name = '數量'

            // 計算並設置內部圖表寬度以支持橫向滾動：每個點至少佔用 pxPerPoint 寬度
            const pxPerPoint = 60
            const minWidth = 300
            this.chartInnerWidth = Math.max(minWidth, displayDates.length * pxPerPoint)

            // 設置 x 軸刻度間隔，目標是最多顯示大約 6 個刻度標籤
            const maxVisibleTicks = 6
            const interval = Math.max(1, Math.ceil(displayDates.length / maxVisibleTicks))
            this.mixChartOpts.xAxis.interval = interval
        },
		exportReport() {
			// 簡化實現：提示導出成功，真實項目可在此構造 CSV/Excel 並調用後端導出
			if (!this.filteredForecasts.length) {
				return uni.showToast({ title: '當前無數據可導出', icon: 'none' })
			}
			uni.showModal({
				title: '提示',
				content: '需求預測報表已導出（示例：可接入後端生成Excel並發送郵件）。',
				showCancel: false
			})
		},
		async loadStoreOptions() {
			try {
				// 使用公開API獲取門店列表
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回的原始格式，與首頁保持一致
					this.storeOptions = res.data
				}
			} catch (e) {
				console.error('加載門店列表失敗', e)
				// 保持空數組
				this.storeOptions = []
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

/* 篩選卡片 */
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
.filter-item.two-thirds {
	flex-basis: 65%;
}
.filter-item.one-third {
	flex-basis: 30%;
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
.sku-search {
	display: flex;
	align-items: center;
	gap: 10rpx;
	.input-border {
		flex: 1;
		border: 1px solid #ddd;
		padding: 10rpx 14rpx;
		border-radius: 8rpx;
		font-size: 26rpx;
		background-color: #fff;
	}
	.btn-mini {
		background: #0066CC;
		color: #fff;
		padding: 0 20rpx;
		border-radius: 999rpx;
		font-size: 24rpx;
		height: 60rpx;
		line-height: 60rpx;
	}
}
.status-tabs {
	display: flex;
	gap: 10rpx;
	flex-wrap: wrap;
}
.status-tab {
	padding: 8rpx 18rpx;
	border-radius: 999rpx;
	font-size: 24rpx;
	background: #f2f4f8;
	color: #555;
}
.status-tab.active {
	background: #0066CC;
	color: #fff;
}
.status-tab.normal.active {
	background: #28a745;
}
.status-tab.shortage.active {
	background: #DC3545;
}
.status-tab.overstock.active {
	background: #FFC107;
	color: #333;
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
	.btn-toggle {
		font-size: 24rpx;
		padding: 0 20rpx;
		border-radius: 999rpx;
		border: 1px solid #ccc;
		background: #fff;
		color: #666;
	}
	.btn-toggle.active {
		border-color: #0066CC;
		color: #0066CC;
		background: #e8f4fd;
	}
	.btn-primary {
		background: #0066CC;
		color: #fff;
		font-size: 24rpx;
		padding: 0 24rpx;
		border-radius: 999rpx;
	}
}

/* 圖表區域 */
.chart-box {
	width: 100%;
	height: 650rpx;
	background: #fff;
	border-radius: 20rpx;
	padding: 24rpx 16rpx;
	box-sizing: border-box;
	overflow-x: auto; /* allow horizontal scroll when chart is wider than container */
}

/* 內部容器允許設置最小寬度以觸發橫向滾動 */
.chart-inner {
    display: block;
    min-width: 800px;
}

/* 列表表格 */
.stats-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 20rpx 24rpx;
	background: #fff;
	border-radius: 16rpx;
	margin-bottom: 16rpx;
	margin-top: 24rpx;
	font-size: 26rpx;
	color: #666;
}
.table-wrapper {
	margin-top: 16rpx;
	background: #fff;
	border-radius: 16rpx;
	overflow: hidden;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.03);
}
.table-header,
.table-row {
	display: flex;
	padding: 18rpx 20rpx;
	font-size: 24rpx;
}
.table-header {
	background: #f5f7fb;
	font-weight: bold;
	color: #666;
}
.table-row:nth-child(2n) {
	background: #fafbff;
}
.col {
	&.store {
		width: 22%;
	}
	&.sku {
		width: 30%;
	}
	&.date {
		width: 18%;
	}
	&.qty {
		width: 15%;
	}
	&.status {
		width: 15%;
		text-align: right;
	}
}
.sku-cell {
	display: flex;
	flex-direction: column;
	.sku-id {
		font-weight: bold;
		color: #333;
	}
	.sku-name {
		font-size: 22rpx;
		color: #777;
	}
}
.status-pill {
	display: inline-flex;
	align-items: center;
	gap: 6rpx;
	font-size: 22rpx;
	padding: 4rpx 12rpx;
	border-radius: 999rpx;
	background: #e8f5e9;
	color: #2e7d32;
}
.status-pill.shortage {
	background: #ffebee;
	color: #DC3545;
}
.status-pill.overstock {
	background: #fff8e6;
	color: #856404;
}

.hint {
	text-align: center;
	padding: 60rpx 24rpx;
	font-size: 28rpx;
	color: #666;
	&.error {
		color: #DC3545;
	}
}

@media screen and (max-width: 960px) {
	.filter-item.half,
	.filter-item.two-thirds,
	.filter-item.one-third {
		flex-basis: 100%;
	}
	.table-header,
	.table-row {
		font-size: 22rpx;
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