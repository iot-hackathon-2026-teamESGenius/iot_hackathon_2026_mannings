<template>
	<view class="container">
		<AppNavBar title="需求预测" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 筛选区 -->
			<view class="filter-card">
				<view class="filter-row">
					<view class="filter-item half">
						<text class="label">预测日期范围</text>
						<uni-datetime-picker
							type="daterange"
							v-model="filters.dateRange"
							:border="true"
							@change="onDateChange"
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
					<view class="filter-item two-thirds">
						<text class="label">选择商品</text>
						<view class="sku-selector">
							<view 
								v-for="sku in skuOptions" 
								:key="sku.id"
								class="sku-chip"
								:class="{ active: selectedSkus.includes(sku.id) }"
								@click="toggleSku(sku.id)"
							>
								{{ sku.name }}
							</view>
						</view>
					</view>
					<view class="filter-item one-third" v-if="displayMode !== 'chart'">
						<text class="label">库存状态</text>
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
							图表
						</button>
						<button class="btn-primary" size="mini" @click="exportReport">导出报表</button>
					</view>
				</view>
			</view>

			<!-- 加载与错误提示 -->
			<view v-if="loading" class="hint">加载中...</view>
			<view v-else-if="errorMsg" class="hint error">{{ errorMsg }}</view>

			<!-- 图表模式 -->
			<view v-else-if="displayMode === 'chart'">
				<uni-section title="需求趋势" type="line" padding>
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
					<text>共 {{ filteredForecasts.length }} 条预测 · 需求合计 {{ totalForecast }} 件</text>
				</view>

				<view class="table-wrapper" v-if="filteredForecasts.length">
					<view class="table-header">
						<text class="col store">门店</text>
						<text class="col sku">商品</text>
						<text class="col date">日期</text>
						<text class="col qty" @click="toggleSort">预测量(件)▼</text>
						<text class="col factors">影响因素</text>
						<text class="col status">状态</text>
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
						<text class="col date">{{ formatDate(item.date) }}</text>
						<text class="col qty">{{ item.forecast_demand }} 件</text>
						<view class="col factors">
							<view class="factor-tags" v-if="item.factors && item.factors.length">
								<text 
									v-for="(factor, fi) in item.factors" 
									:key="fi"
									class="factor-tag"
								>{{ factor }}</text>
							</view>
							<text v-else class="no-factor">基础预测</text>
						</view>
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
					暂无需求预测数据
				</view>
			</template>

			<view class="tab-bar-placeholder"></view>
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
					<view 
						v-for="store in displayedStores" 
						:key="store.store_id"
						class="store-item"
						:class="{ selected: filters.storeId === store.store_id }"
						@click="selectStore(store)"
					>
						<view class="store-info">
							<text class="store-name">{{ store.store_name }}</text>
							<text class="store-detail">ID: {{ store.store_id }} · {{ store.district || '未知地区' }}</text>
						</view>
						<uni-icons v-if="filters.storeId === store.store_id" type="checkmarkempty" size="18" color="#0066CC"></uni-icons>
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
import { apiGet, getSelectedStore } from '../../utils/api.js'

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
				skuIds: 'SKU001', // 默认商品 SKU001
				status: 'all' // all / normal / shortage / overstock
			},
			storeOptions: [],
			// 商品选项
			skuOptions: [
				{ id: 'SKU001', name: '维他命C 1000mg' },
				{ id: 'SKU002', name: '感冒灵颗粒' },
				{ id: 'SKU003', name: '洗手液 500ml' },
				{ id: 'SKU004', name: '口罩 50片装' },
				{ id: 'SKU005', name: '消毒湿巾' }
			],
			selectedSkus: ['SKU001'], // 默认选中第一个
			statusOptions: [
				{ value: 'all', text: '全部' },
				{ value: 'normal', text: '正常' },
				{ value: 'shortage', text: '缺货' },
				{ value: 'overstock', text: '积压' }
			],

			// 原始数据与过滤后数据
			forecasts: [],

			// 图表数据（混合：预测折线 + 实际柱状）
			mixChartData: { categories: [], series: [] },
			// 尝试这种方式
			mixChartOpts: {
			  // 图表标题配置
			  title: {
			    name: '需求趋势',
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
			    
			    // 添加轴标题
			    title: {
			      name: '数量(件)',
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
			// 动态计算图表内部宽度（用于横向滚动）
			chartInnerWidth: 600,

			// UI 状态
			loading: false,
			errorMsg: '',
			displayMode: 'chart', // 默认以图表展示
			sortDesc: true,
			// 门店选择模态框
			showStoreModal: false,
			storeSearchText: '',
			displayLimit: 20 // 初始显示的门店数量
		}
	},
	computed: {
		// 按筛选条件得到的列表
		filteredForecasts() {
			let list = this.forecasts.slice()
			if (this.filters.status !== 'all') {
				list = list.filter((i) => i._stock_status === this.filters.status)
			}
			return list
		},
		// 排序后的列表（按预测量）
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
			if (!this.filters.storeId) return '请选择门店'
			const store = this.storeOptions.find(s => s.store_id === this.filters.storeId)
			return store ? store.store_name : '请选择门店'
		}
	},
	onLoad() {
		// 默认使用首页当前选择的门店
		const selected = getSelectedStore && getSelectedStore()
		if (selected && selected.store_id) {
			this.filters.storeId = selected.store_id
		}
		this.displayMode = 'chart'
		// 先加载门店列表，然后再决定是否预测
		this.loadStoreOptionsAndFetch()
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
			this.fetchForecast()
		},
		loadMoreStores() {
			this.displayLimit += 20 // 每次加载20个更多门店
		},
		// 切换SKU选中状态
		toggleSku(skuId) {
			const idx = this.selectedSkus.indexOf(skuId)
			if (idx >= 0) {
				// 已选中，取消选中（但至少保留1个）
				if (this.selectedSkus.length > 1) {
					this.selectedSkus.splice(idx, 1)
				}
			} else {
				// 未选中，添加
				this.selectedSkus.push(skuId)
			}
			// 同步到 filters.skuIds
			this.filters.skuIds = this.selectedSkus.join(',')
			this.fetchForecast()
		},
		onDateChange() {
			this.fetchForecast()
		},
		changeStatus(v) {
			this.filters.status = v
		},
		resetFilters() {
			this.selectedSkus = ['SKU001']
			this.filters.skuIds = 'SKU001'
			this.filters.status = 'all'
			// 保留当前门店，只重置 SKU/状态
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
				shortage: '缺货',
				overstock: '积压'
			}
			return map[s] || s || '正常'
		},
		// 格式化日期，显示星期几
		formatDate(dateStr) {
			if (!dateStr) return ''
			const d = new Date(dateStr)
			const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
			const month = String(d.getMonth() + 1).padStart(2, '0')
			const day = String(d.getDate()).padStart(2, '0')
			const weekday = weekdays[d.getDay()]
			return `${month}-${day} ${weekday}`
		},
		async fetchForecast() {
			const [start, end] = this.filters.dateRange || []
			if (!start || !end) {
				uni.showToast({ title: '请先选择日期范围', icon: 'none' })
				return
			}
			if (!this.filters.storeId) {
				uni.showToast({ title: '请选择门店', icon: 'none' })
				return
			}
			if (!this.selectedSkus.length) {
				uni.showToast({ title: '请至少选择一个商品', icon: 'none' })
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
				// SKU ID 列表，逗号分隔
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
				console.error('获取需求预测失败', e)
				this.errorMsg = '加载失败，请确认后端已启动'
				uni.showToast({ title: '加载失败', icon: 'none' })
			} finally {
				this.loading = false
			}
		},
		// 通过预测值与上下界粗略推断库存状态
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
                this.mixChartData = { title: { name: '需求预测' }, categories: [], series: [] }
                this.mixChartOpts.title.name = '需求预测'
                return
            }
            // 维度：日期 + SKU
            const dateSet = new Set()
            const skuSet = new Set()
            list.forEach((i) => {
                if (i.date) dateSet.add(i.date)
                if (i.sku_id) skuSet.add(i.sku_id)
            })
            const dates = Array.from(dateSet).sort()
            // 横坐标显示去掉年份，只保留 MM-DD
            const displayDates = dates.map(d => (typeof d === 'string' && d.length >= 5) ? d.slice(5) : d)
            let skus = Array.from(skuSet)
            // 如果没有检测到 SKU，则使用 filters.skuIds（可能为逗号分隔）或回退到默认 SKU001
            if (!skus.length) {
                if (this.filters.skuIds && this.filters.skuIds.trim()) {
                    skus = this.filters.skuIds.split(',').map(s => s.trim()).filter(Boolean)
                }
                if (!skus.length) skus = ['SKU001']
            }

            const series = []
            // 为不同SKU分配不同颜色
            const skuColors = [
                { forecast: '#FF7F50', actual: '#2F90FF' },  // 橙/蓝
                { forecast: '#28a745', actual: '#6c757d' },  // 绿/灰
                { forecast: '#dc3545', actual: '#17a2b8' },  // 红/青
                { forecast: '#6f42c1', actual: '#fd7e14' },  // 紫/橙
                { forecast: '#e83e8c', actual: '#20c997' }   // 粉/绿青
            ]
            
            skus.forEach((skuId, idx) => {
                // 获取产品名称
                const skuItem = list.find(i => i.sku_id === skuId && i.sku_name)
                const skuName = (skuItem && skuItem.sku_name) ? skuItem.sku_name : skuId
                const colorPair = skuColors[idx % skuColors.length]
                
                const forecastArr = []
                const actualArr = []
                dates.forEach((d) => {
                    const items = list.filter((i) => i.sku_id === skuId && i.date === d)
                    const fSum = items.reduce((s, it) => s + (it.forecast_demand || 0), 0)
                    const aSum = items.reduce((s, it) => s + (it.actual_demand || 0), 0)
                    forecastArr.push(Number(fSum.toFixed(1)))
                    actualArr.push(Number(aSum.toFixed(1)))
                })
                // 预测：折线
                series.push({
                    name: `${skuName} 预测`,
                    type: 'line',
                    data: forecastArr,
                    itemStyle: { color: colorPair.forecast },
                    label: { show: true, color: colorPair.forecast, position: 'top', formatter: '{c}件' },
                    smooth: true
                })
                // 实际：柱状
                series.push({
                    name: `${skuName} 实际`,
                    type: 'column',
                    data: actualArr,
                    itemStyle: { color: colorPair.actual },
                    label: { show: true, color: '#ffffff', position: 'inside', formatter: '{c}件' },
                    barGap: '30%'
                })
            })

            // 计算标题：单 SKU 使用 sku_name（优先）或 skuId，否则回退到默认
            let chartTitle = '需求趋势'
			
            if (skus.length === 1) {
                const skuIdPrimary = skus[0]
                const skuNameItem = this.forecasts.find(i => i.sku_id === skuIdPrimary && i.sku_name)
                const skuLabel = (skuNameItem && skuNameItem.sku_name) ? skuNameItem.sku_name : (skuIdPrimary || 'SKU001')
                chartTitle = `${skuLabel} 需求趋势`
            } else {
                chartTitle = '需求趋势'
            }
            // 如果有门店筛选，加入门店名前缀（可选）
            if (this.filters.storeId) {
                const store = this.storeOptions.find(s => s.value === this.filters.storeId)
                if (store && store.text) {
                    chartTitle = `${store.text} ${chartTitle}`
                }
            }

            // 把标题写入 opts 和 data（组件可能从不同位置读取）
            this.mixChartOpts.title.name = chartTitle
            // mixChartData.title 使用对象形式，避免字符串->对象访问导致 undefined
            this.mixChartData = {
                title: { name: chartTitle },
                categories: displayDates,
                series
            }

            // 给 x/y 轴添加 name（如果需要显示轴标题）
            this.mixChartOpts.xAxis.name = '日期'
            this.mixChartOpts.yAxis.name = '数量(件)'

            // 计算并设置内部图表宽度以支持横向滚动：每个点至少占用 pxPerPoint 宽度
            const pxPerPoint = 60
            const minWidth = 300
            this.chartInnerWidth = Math.max(minWidth, displayDates.length * pxPerPoint)

            // 设置 x 轴刻度间隔，目标是最多显示大约 6 个刻度标签
            const maxVisibleTicks = 6
            const interval = Math.max(1, Math.ceil(displayDates.length / maxVisibleTicks))
            this.mixChartOpts.xAxis.interval = interval
        },
		exportReport() {
			// 简化实现：提示导出成功，真实项目可在此构造 CSV/Excel 并调用后端导出
			if (!this.filteredForecasts.length) {
				return uni.showToast({ title: '当前无数据可导出', icon: 'none' })
			}
			uni.showModal({
				title: '提示',
				content: '需求预测报表已导出（示例：可接入后端生成 Excel 并发送邮件）。',
				showCancel: false
			})
		},
		async loadStoreOptions() {
			try {
				// 使用公开API获取门店列表
				const res = await apiGet('/auth/stores/public', { params: {} })
				if (res && res.success && res.data && res.data.length) {
					// 直接使用API返回的原始格式，与首页保持一致
					this.storeOptions = res.data
					return res.data
				}
			} catch (e) {
				console.error('加载门店列表失败', e)
			}
			this.storeOptions = []
			return []
		},
		
		// 加载门店并决定是否预测
		async loadStoreOptionsAndFetch() {
			const stores = await this.loadStoreOptions()
			
			// 如果没有选中门店，默认选择第一个门店
			if (!this.filters.storeId && stores.length > 0) {
				this.filters.storeId = stores[0].store_id
			}
			
			// 只有选中了门店才执行预测
			if (this.filters.storeId) {
				this.fetchForecast()
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

/* 筛选卡片 */
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

/* SKU选择器样式 */
.sku-selector {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
}
.sku-chip {
	padding: 12rpx 24rpx;
	border-radius: 999rpx;
	font-size: 24rpx;
	background: #f2f4f8;
	color: #555;
	border: 2rpx solid transparent;
	cursor: pointer;
	transition: all 0.2s;
	
	&:hover {
		background: #e8f4fd;
	}
	
	&.active {
		background: #0066CC;
		color: #fff;
		border-color: #0066CC;
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

/* 图表区域 */
.chart-box {
	width: 100%;
	height: 650rpx;
	background: #fff;
	border-radius: 20rpx;
	padding: 24rpx 16rpx;
	box-sizing: border-box;
	overflow-x: auto; /* allow horizontal scroll when chart is wider than container */
}

/* 内部容器允许设置最小宽度以触发横向滚动 */
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
		width: 18%;
	}
	&.sku {
		width: 22%;
	}
	&.date {
		width: 16%;
	}
	&.qty {
		width: 12%;
	}
	&.factors {
		width: 20%;
	}
	&.status {
		width: 12%;
		text-align: right;
	}
}

/* 影响因素标签 */
.factor-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 4rpx;
}
.factor-tag {
	padding: 4rpx 10rpx;
	border-radius: 6rpx;
	font-size: 20rpx;
	background: #e8f4fd;
	color: #0066CC;
	white-space: nowrap;
}
.no-factor {
	font-size: 20rpx;
	color: #999;
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
	display: flex;
	align-items: center;
	justify-content: space-between;
	
	&:hover {
		background: #f8f9fa;
	}
	
	&:active {
		background: #e9ecef;
	}
	
	&.selected {
		background: #e8f4fd;
		border-left: 4rpx solid #0066CC;
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