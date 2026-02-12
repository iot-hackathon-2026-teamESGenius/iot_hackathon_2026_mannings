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
						<uni-data-select
							v-model="filters.storeId"
							:localdata="storeOptions"
							placeholder="全部门店"
							@change="fetchForecast"
						/>
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
							<button class="btn-mini" size="mini" @click="applyFilters">搜索</button>
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
					<text>共 {{ filteredForecasts.length }} 条 · 需求合计 {{ totalForecast }} 件</text>
				</view>

				<view class="table-wrapper" v-if="filteredForecasts.length">
					<view class="table-header">
						<text class="col store">门店</text>
						<text class="col sku">SKU</text>
						<text class="col date">日期</text>
						<text class="col qty" @click="toggleSort">预测量▼</text>
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
					暂无需求预测数据
				</view>
			</template>

			<view class="tab-bar-placeholder"></view>
		</scroll-view>

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
			storeOptions: [
				{ value: '', text: '全部门店' },
				{ value: 'M001', text: 'Mannings Tsim Sha Tsui' },
				{ value: 'M002', text: 'Mannings Causeway Bay' },
				{ value: 'M003', text: 'Mannings Central' },
				{ value: 'M004', text: 'Mannings Mongkok' },
				{ value: 'M005', text: 'Mannings Sha Tin' }
			],
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
			sortDesc: true
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
		}
	},
	onLoad() {
		// 默认使用首页当前选择的门店
		const selected = getSelectedStore && getSelectedStore()
		if (selected && selected.store_id) {
			this.filters.storeId = selected.store_id
		}
		this.displayMode = 'chart'
		this.fetchForecast()
	},
	methods: {
		goBack() {
			uni.navigateBack()
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
			if (!this.filters.skuIds || !this.filters.skuIds.trim()) {
				uni.showToast({ title: '请输入 SKU ID 列表', icon: 'none' })
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
                // 预测：折线，颜色 & 标签在上方
                series.push({
                    name: `${skuId || 'SKU001'} 预测`,
                    type: 'line',
                    data: forecastArr,
                    itemStyle: { color: '#FF7F50' }, // 橙色
                    label: { show: true, color: '#FF7F50', position: 'top' },
                    smooth: true
                })
                // 实际：柱状，颜色与标签位置不同，标签放在柱内避免与折线标签遮挡
                series.push({
                    name: `${skuId || 'SKU001'} 实际`,
                    type: 'column',
                    data: actualArr,
                    itemStyle: { color: '#2F90FF' }, // 蓝色柱子
                    label: { show: true, color: '#ffffff', position: 'inside' }, // 白色字体在柱内
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
            this.mixChartOpts.yAxis.name = '数量'

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
</style>