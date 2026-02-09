<template>
	<view class="container">
		<AppNavBar title="车队调度与路径规划" :show-back="true" :show-menu="false" @back="goBack" />


		<view class="main-layout">

			<view class="layout-center panel-box" :style="{ height: mapHeightCom }">
				<map
					id="deliveryMap"
					class="map-view"
					:style="{ height: mapHeightCom }"
					:latitude="mapCenter.lat"
					:longitude="mapCenter.lng"
					:markers="mapMarkers"
					:polyline="mapPolylines"
					:scale="mapScale"
					show-location
					@markertap="handleMarkerTap"
				></map>
			</view>

			<view class="layout-right panel-box" :class="{ collapsed: !isListOpen }">
				<view class="panel-header panel-header-clickable" @click="toggleList">
					<text class="title">调度明细列表</text>
					<view class="sort-icons">
						<uni-icons type="list" size="20" color="#666" @click.stop="sortList('status')"></uni-icons>
						<uni-icons :type="isListOpen ? 'top' : 'bottom'" size="18" color="#666"></uni-icons>
					</view>
				</view>
				<scroll-view v-show="isListOpen" scroll-y class="panel-content list-content">
					<view class="table-header desktop-only">
						<text class="col-1">车辆</text>
						<text class="col-2">司机/时间</text>
						<text class="col-3">状态</text>
					</view>

					<view
						class="schedule-item"
						v-for="(item, index) in scheduleList"
						:key="index"
						@click="focusVehicle(item)"
						:class="{ active: currentVehicleId === item.vehicle_id }"
					>
						<view class="item-main">
							<view class="vehicle-info">
								<text class="v-id">{{ item.vehicle_id }}</text>
								<text class="v-type">{{ item.vehicle_type || 'HGV' }}</text>
							</view>
							<view class="driver-info">
								<text class="name">{{ item.driver_name }}</text>
								<text class="time">出发: {{ item.departure_time }}</text>
								<text class="stores">配送门店: {{ item.store_list.length }}家</text>
							</view>
							<view class="status-info">
								<uni-tag :text="formatStatus(item.status)" :type="getStatusType(item.status)" size="small" />
								<text class="cost">HK${{ item.estimated_cost }}</text>
								<button class="mini-adjust" @click.stop="openAdjustModal(item)">调整</button>
							</view>
						</view>

						<view class="abnormal-bar" v-if="item.status === 'abnormal'" @click.stop="showAbnormalDetail(item)">
							<uni-icons type="info-filled" color="#dc3545" size="14"></uni-icons>
							<text>点击查看异常原因</text>
						</view>
					</view>

					<uni-load-more v-if="loading" status="loading"></uni-load-more>
					<view v-if="scheduleList.length === 0 && !loading" class="empty-tip">暂无调度数据</view>
				</scroll-view>
			</view>

		</view>
		<AppTabBar />

		<uni-popup ref="abnormalPopup" type="center">
			<view class="popup-card warning">
				<view class="popup-title">异常详情</view>
				<view class="popup-content">
					<view class="row"><text class="label">车辆编号：</text>{{ abnormalItem.vehicle_id }}</view>
					<view class="row"><text class="label">异常原因：</text>{{ abnormalItem.abnormal_reason || '交通拥堵导致预计延迟30分钟' }}</view>
					<view class="advice-box">
						<text class="advice-title">系统建议：</text>
						<text>建议重新规划路线或分配临近车辆 (V005) 分担部分门店。</text>
					</view>
				</view>
				<button class="btn-primary full-width" @click="$refs.abnormalPopup.close()">关闭</button>
			</view>
		</uni-popup>

		<uni-popup ref="adjustPopup" type="center" :is-mask-click="false">
			<view class="popup-card">
				<view class="popup-title">调整调度方案</view>
				<scroll-view scroll-y class="adjust-form">
					<view v-if="adjustForm.vehicle_id" class="form-item">
						<text class="label">当前车辆</text>
						<view class="current-vehicle">{{ adjustForm.vehicle_id }}</view>
					</view>
					<view class="form-item">
						<text class="label">选择车辆</text>
						<uni-data-select v-model="adjustForm.vehicle_id" :localdata="vehicleSelectData"></uni-data-select>
					</view>
					<view class="form-item">
						<text class="label">新出发时间</text>
						<uni-datetime-picker type="time" v-model="adjustForm.departure_time" :border="true" />
					</view>
					<view class="form-item">
						<text class="label">指派司机</text>
						<input class="uni-input input-border" v-model="adjustForm.driver_id" placeholder="输入司机ID" />
					</view>
					<view v-if="adjustForm.store_list && adjustForm.store_list.length" class="form-item">
						<text class="label">当前门店顺序</text>
						<view class="store-seq">{{ adjustForm.store_list.join(' → ') }}</view>
					</view>
				</scroll-view>
				<view class="btn-group">
					<button class="btn-outline" @click="$refs.adjustPopup.close()">取消</button>
					<button class="btn-primary" @click="submitAdjustment">确认调整</button>
				</view>
			</view>
		</uni-popup>

	</view>
</template>

<script>

import { apiGet, apiPut } from '../../utils/api.js'
import AppNavBar from '../../components/app-nav-bar.vue'
import AppTabBar from '../../components/app-tab-bar.vue'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		return {
			// 面板折叠：点击标题展开/收起（让地图可视区域更大）
			isListOpen: true,

			//  核心数据
			scheduleList: [], // 调度列表数据 [cite: 199]
			mapMarkers: [],   // 地图标记点 (Store, DC, Vehicle)
			mapPolylines: [], // 路径规划线 [cite: 219]
			currentVehicleId: '', // 当前选中的车辆
			loading: false,
			isTracking: false, // 是否开启实时追踪
			timer: null,      // 实时追踪定时器

			// 缓存从后端返回的 routes 数据，便于根据 vehicle_id 查找
			cachedRoutes: [],

			// DC 坐标缓存（由 map-data 提供）
			mapDcLocation: null,

			// 本地生成的 numeric marker id 计数器，保证在各平台上 markerId 一致为数字
			markerIdCounter: 1000,

			// 是否使用静态图片作为标注图标（优先使用内置样式，若存在静态图则回退使用图片）
			useStaticIcons: {
				store: true,
				dc: true,
				car: true,
				carActive: true
			},

			// 3. 地图配置
			mapCenter: { lat: 22.3193, lng: 114.1694 }, // 香港中心坐标
			mapScale: 11,

			// 4. 弹窗数据
			abnormalItem: {},
			adjustForm: {
				vehicle_id: '',
				departure_time: '08:00',
				driver_id: '',
				store_list: []
			}
		}
	},
	computed: {
		// 参考 pure_map.vue：给地图一个“显式高度”，避免在 flex/scroll 布局里高度塌陷导致地图不显示
		mapHeightCom() {
			const systemInfo = uni.getSystemInfoSync()
			const statusBar = systemInfo.statusBarHeight || 0
			// nav-bar 88rpx 约等于 44px（以 750rpx = 屏宽为基准）
			const navBarPx = 44 + statusBar
			const tabBarPx = 50
			const paddings = 16
			const h = Math.max(320, systemInfo.windowHeight - navBarPx - tabBarPx - paddings)
			return `${h}px`
		},
		// 将 scheduleList 转换为下拉选框数据
		vehicleSelectData() {
			return this.scheduleList.map(item => ({
				value: item.vehicle_id,
				text: `${item.vehicle_id} - ${item.driver_name}`
			}))
		}
	},
	onLoad() {
		// 小屏默认折叠，让地图优先可见；点击标题再展开筛选/明细
		try {
			const info = uni.getSystemInfoSync()
			if (info && info.windowWidth && info.windowWidth <= 960) {
				this.isListOpen = false
			}
		} catch (e) {}
		this.fetchSchedules()
	},
	onUnload() {
		this.stopTracking()
	},
		methods: {
		toggleList() {
			this.isListOpen = !this.isListOpen
		},
		goBack() {
			uni.navigateBack()
		},
		refreshData() {
			this.fetchSchedules()
			uni.showToast({ title: '数据已刷新', icon: 'none' })
		},

		// API 1: 获取调度列表 
		async fetchSchedules() {
			this.loading = true
			try {
				// 构造查询参数
				// const params = {
				// 	schedule_date: this.filters.date,
				// 	vehicle_type: this.filters.vehicleType || null,
				// 	status: null // 可根据需要添加状态筛选
				// }
                
				// const res = await apiGet('/planning/schedules', { params })
				const res = await apiGet('/planning/schedules')
				if (res && res.success) {
					this.scheduleList = res.data.schedules || []
					// 获取列表后，加载地图上的门店/DC和默认路线（cachedRoutes）
					await this.fetchMapData()
					// 同步获取一次实时位置以标注车辆
					await this.fetchRealTimePositions()
				}
			} catch (e) {
				console.error('获取调度列表失败', e)
				// // 模拟数据用于展示 UI 效果
				// this.mockData() 
			} finally {
				this.loading = false
			}
		},

		// API 2: 获取地图路线/门店/DC 数据并在地图上标注（使用 /planning/routes/map-data）
		async fetchMapData() {
			try {
				const res = await apiGet('/planning/routes/map-data')
				if (res && res.success && res.data) {
					const data = res.data
					// 缓存 routes
					this.cachedRoutes = data.routes || []

					// 缓存 DC 坐标，方便把未出发的车辆放在起点
					this.mapDcLocation = data.dc_location || null

					const markers = []

						// DC 标注（使用 numeric id + entity），优先使用内置样式
						if (data.dc_location) {
							const base = { id: this.getNextMarkerId(), entity: 'DC', latitude: data.dc_location.lat, longitude: data.dc_location.lng, width: 34, height: 34, callout: { content: '配送中心', display: 'ALWAYS' } }
							if (this.useStaticIcons.dc) base.iconPath = '/static/img/DC.png'
							else base.label = { content: 'DC', color: '#ffffff', bgColor: '#2e7d32', padding: 6, borderRadius: 6 }
							markers.push(base)
						}

					// 门店标注
					if (data.store_locations) {
						Object.keys(data.store_locations).forEach((storeId) => {
							const s = data.store_locations[storeId]
							const base = { id: this.getNextMarkerId(), entity: storeId, latitude: s.lat, longitude: s.lng, width: 22, height: 22, callout: { content: s.name } }
							if (this.useStaticIcons.store) base.iconPath = '/static/img/store.png'
							else base.label = { content: 'S', color: '#fff', bgColor: '#0066CC', padding: 6, borderRadius: 6 }
							markers.push(base)
						})
					}

					// 初始不添加车辆标记，车辆会在 fetchRealTimePositions 中加入（或以状态放到起点/终点）
					this.mapMarkers = markers

					// 如果之前选中了某辆车，重建其路线展示
					if (this.currentVehicleId) {
						const selected = this.currentVehicleId
						const route = this.cachedRoutes.find(r => r.vehicle_id === selected)
						if (route) {
							this.mapPolylines = [{ points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: '#0066CC', width: 4 }]
						}
					}
				}
			} catch (e) {
				console.log('地图数据加载错误...', e)
			}
		},

		// API 3: 实时位置追踪和基于 status 的候补位置放置
		async fetchRealTimePositions() {
			try {
				const res = await apiGet('/planning/vehicles/realtime')
				const positions = (res && res.success && res.data && Array.isArray(res.data.positions)) ? res.data.positions : []

				// 复制现有标记（门店/DC）
				const newMarkers = [...this.mapMarkers]

				// 将实时返回的位置更新到标记集合
				positions.forEach((p) => {
					// 先尝试通过 entity 匹配（我们为每个标记设置了 entity 字段），兼容老逻辑
					let idx = newMarkers.findIndex(m => m.entity === p.vehicle_id || m.id === p.vehicle_id)
					const vehicleMarker = {
						id: idx !== -1 ? newMarkers[idx].id : this.getNextMarkerId(),
						entity: p.vehicle_id,
						latitude: p.lat,
						longitude: p.lng,
						width: 28,
						height: 28,
						callout: { content: `${p.vehicle_id} (${p.driver})`, display: 'BYCLICK' }
					}
					if (this.useStaticIcons.carActive) vehicleMarker.iconPath = '/static/img/car-active.png'
					else vehicleMarker.label = { content: p.vehicle_id, color: '#fff', bgColor: '#FD7E14', padding: 6, borderRadius: 6 }

					if (idx !== -1) {
						newMarkers[idx] = Object.assign({}, newMarkers[idx], vehicleMarker)
					} else {
						newMarkers.push(vehicleMarker)
					}
				})


				this.mapMarkers = newMarkers

				// 如果当前选中车辆有实时位置，居中地图到该车
				if (this.currentVehicleId) {
					const cur = positions.find(p => p.vehicle_id === this.currentVehicleId)
					if (cur) {
						this.mapCenter = { lat: cur.lat, lng: cur.lng }
					}
				}
			} catch (e) {
				console.error('实时位置获取失败', e)
			}
		},

		// 开启/停止实时追踪
		// toggleRealtimeTracking() {
		// 	this.isTracking = !this.isTracking
		// 	if (this.isTracking) {
		// 		uni.showToast({ title: '开始实时追踪', icon: 'none' })
		// 		this.fetchRealTimePositions() // 立即执行一次
		// 		this.timer = setInterval(this.fetchRealTimePositions, 5000) // 每5秒轮询
		// 	} else {
		// 		this.stopTracking()
		// 		uni.showToast({ title: '已停止追踪', icon: 'none' })
		// 	}
		// },

		stopTracking() {
			if (this.timer) {
				clearInterval(this.timer)
				this.timer = null
			}
		},

		// API 4: 调整调度方案
		openAdjustModal(item) {
			// 从“明细列表每行按钮”进入：预填充该车信息
			if (item && item.vehicle_id) {
				this.adjustForm.vehicle_id = item.vehicle_id
				this.adjustForm.departure_time = item.departure_time || this.adjustForm.departure_time
				// 后端字段是 driver_id，这里先用现有的 driver_name 兜底展示（如后端补充 driver_id 可直接替换）
				this.adjustForm.driver_id = item.driver_id || item.driver_name || ''
				this.adjustForm.store_list = Array.isArray(item.store_list) ? item.store_list : []
			}
			this.$refs.adjustPopup.open()
		},
		async submitAdjustment() {
			if (!this.adjustForm.vehicle_id) return uni.showToast({title:'请选择车辆', icon:'none'})
			
			const vehicleId = this.adjustForm.vehicle_id
			const payload = {
				departure_time: this.adjustForm.departure_time,
				driver_id: this.adjustForm.driver_id,
				operator: 'Admin', // 当前用户
				// store_list: ... 需要完整的逻辑来处理重新分配
			}

			try {
				const res = await apiPut(`/planning/schedules/${vehicleId}/adjust`, payload)
				if (res) { // 假设 200 OK
					uni.showToast({ title: '调整方案已提交', icon: 'success' })
					this.$refs.adjustPopup.close()
					this.fetchSchedules() // 刷新列表
				}
			} catch (e) {
				uni.showToast({ title: '提交失败', icon: 'none' })
			}
		},

		// 辅助：处理地图点击
		handleMarkerTap(e) {
			const markerId = e && e.detail ? e.detail.markerId : null
			// markerId 可能为数字（各平台不同），我们优先通过 numeric id 查找，再通过 entity 字符串匹配
			let marker = null
			if (markerId !== null && markerId !== undefined) {
				marker = this.mapMarkers.find(m => m.id === markerId || m.id === Number(markerId) || m.entity === markerId || m.entity === String(markerId))
			}
			if (!marker) return
			if (marker.entity && typeof marker.entity === 'string' && marker.entity.startsWith('V')) {
				this.currentVehicleId = marker.entity
				// 选中车辆时同时展示对应路线
				const route = this.cachedRoutes.find(r => r.vehicle_id === marker.entity)
				if (route && route.coordinates) {
					this.mapPolylines = [{ points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: '#0066CC', width: 4 }]
				}
			}
		},

		async focusVehicle(item) {
			this.currentVehicleId = item.vehicle_id

			// 找到对应 route（优先使用已缓存的 route）
			let route = this.cachedRoutes.find(r => r.vehicle_id === item.vehicle_id)
			if (!route) {
				await this.fetchMapData()
				route = this.cachedRoutes.find(r => r.vehicle_id === item.vehicle_id)
			}

			if (route && route.coordinates && route.coordinates.length > 0) {
				this.mapPolylines = [ { points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: '#0066CC', width: 4 } ]
			}

			// 更新并居中到车辆实时位置（如果可用）
			await this.fetchRealTimePositions()
			const vehMarker = this.mapMarkers.find(m => m.entity === item.vehicle_id || m.id === item.vehicle_id)
			if (vehMarker) {
				this.mapCenter = { lat: vehMarker.latitude, lng: vehMarker.longitude }
				this.mapScale = 13
			}
		},

		// 辅助：状态样式
		formatStatus(status) {
			const map = { pending: '待执行', active: '执行中', completed: '已完成', abnormal: '异常' }
			return map[status] || status
		},
		getStatusType(status) {
			const map = { pending: 'primary', active: 'success', completed: 'default', abnormal: 'error' }
			return map[status] || 'default'
		},

		showAbnormalDetail(item) {
			this.abnormalItem = item
			this.$refs.abnormalPopup.open()
		},
		

		// Helper: generate next numeric marker id
		getNextMarkerId() {
			this.markerIdCounter = (this.markerIdCounter || 1000) + 1
			return this.markerIdCounter
		}
	}
}
</script>

<style lang="scss" scoped>
/* 全局容器与变量 */
.container {
	height: 100vh;
	display: flex;
	flex-direction: column;
	background-color: #f4f7f9;
	overflow: hidden;
}

/* 1. 顶部导航栏 (复用首页) */
.nav-bar {
	height: 88rpx;
	padding-top: var(--status-bar-height);
	background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 30rpx;
	color: #fff;
	flex-shrink: 0; /* 防止被挤压 */
	box-shadow: 0 2rpx 10rpx rgba(0,102,204,0.25);

	.nav-title {
		display: flex; align-items: center; gap: 10rpx;
		.page-title { font-size: 32rpx; font-weight: bold; }
	}
}

/* 2. 主体布局 (核心响应式逻辑) */
.main-layout {
	flex: 1;
	display: flex;
	overflow: hidden; /* 内部滚动 */
	padding: 20rpx;
	gap: 20rpx;

	/* 面板通用样式 */
	.panel-box {
		background: #fff;
		border-radius: 16rpx;
		display: flex;
		flex-direction: column;
		box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.05);
		
		.panel-header {
			padding: 20rpx;
			border-bottom: 1px solid #eee;
			display: flex; justify-content: space-between; align-items: center;
			.title { font-weight: bold; font-size: 30rpx; color: #333; border-left: 8rpx solid #0066CC; padding-left: 12rpx; }
		}
		.panel-header-clickable { cursor: pointer; }
		.panel-header-right { display: flex; align-items: center; gap: 12rpx; }
		
		.panel-content {
			flex: 1;
			overflow-y: auto;
			padding: 20rpx;
		}
	}



	/* 中间：地图区 */
	.layout-center {
		flex: 1; /* 占据剩余空间 */
		position: relative;
		padding: 0; /* 地图铺满 */
		overflow: hidden;

		.map-view {
			width: 100%;
			height: 100%;
		}
		
		.map-legend {
			position: absolute;
			top: 20rpx; right: 20rpx;
			background: rgba(255,255,255,0.9);
			padding: 10rpx 20rpx;
			border-radius: 8rpx;
			box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.1);
			
			.legend-item {
				display: flex; align-items: center; font-size: 24rpx; margin: 6rpx 0;
				.dot { width: 16rpx; height: 16rpx; border-radius: 50%; margin-right: 10rpx; }
				.dot.store { background: #0066CC; }
				.dot.dc { background: #2e7d32; }
				.dot.car { background: #FD7E14; }
			}
		}
	}

	/* 右侧：列表区 */
	.layout-right {
		width: 360rpx;
		flex-shrink: 0;

		.table-header {
			display: flex; padding: 0 10rpx 10rpx; border-bottom: 2rpx solid #eee;
			text { font-size: 24rpx; color: #999; font-weight: bold; }
			.col-1 { width: 30%; } .col-2 { width: 45%; } .col-3 { width: 25%; text-align: right; }
		}

		.schedule-item {
			padding: 20rpx;
			border-bottom: 1px solid #f0f0f0;
			cursor: pointer;
			transition: background 0.2s;
			
			&:hover, &.active { background-color: #f0f8ff; }

			.item-main {
				display: flex; justify-content: space-between; align-items: flex-start;
				
				.vehicle-info {
					display: flex; flex-direction: column; width: 25%;
					.v-id { font-weight: bold; color: #333; }
					.v-type { font-size: 22rpx; color: #999; background: #eee; padding: 2rpx 6rpx; border-radius: 4rpx; width: fit-content; margin-top: 4rpx; }
				}
				.driver-info {
					display: flex; flex-direction: column; width: 45%;
					.name { font-size: 26rpx; color: #333; }
					.time { font-size: 22rpx; color: #666; margin-top: 4rpx; }
					.stores { font-size: 22rpx; color: #999; }
				}
				.status-info {
					display: flex; flex-direction: column; align-items: flex-end; width: 30%;
					.cost { font-size: 24rpx; color: #666; margin-top: 8rpx; }
					.mini-adjust {
						margin-top: 10rpx;
						height: 52rpx;
						line-height: 52rpx;
						padding: 0 16rpx;
						font-size: 22rpx;
						background: #e8f4fd;
						color: #0066CC;
					}
				}
			}

			.abnormal-bar {
				margin-top: 16rpx;
				background: #ffebee;
				color: #c62828;
				font-size: 22rpx;
				padding: 8rpx 16rpx;
				border-radius: 8rpx;
				display: flex; align-items: center; gap: 8rpx;
			}
		}
	}
}

/* 3. 底部 TabBar */
.tab-bar-placeholder { height: 100rpx; flex-shrink: 0; }
.custom-tab-bar {
	position: fixed; bottom: 0; left: 0; right: 0;
	height: 100rpx; background: #fff;
	display: flex; border-top: 1px solid #eee; z-index: 99;
	
	.tab-item {
		flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center;
		color: #999; font-size: 20rpx;
		&.active { color: #0066CC; }
		text { margin-top: 6rpx; }
	}
}

/* 4. 弹窗样式 */
.popup-card {
	z-index: 99;
	width: 600rpx;
	background: #fff;
	border-radius: 20rpx;
	padding: 30rpx;
	
	&.warning { border-top: 10rpx solid #dc3545; }
	
	.popup-title { font-size: 34rpx; font-weight: bold; text-align: center; margin-bottom: 30rpx; }
	
	.row { margin-bottom: 20rpx; font-size: 28rpx; .label { color: #999; width: 160rpx; display: inline-block; } }
	
	.advice-box { background: #fff8e6; padding: 20rpx; border-radius: 10rpx; font-size: 26rpx; color: #856404; margin: 30rpx 0; }
	
	.adjust-form {
		max-height: 60vh;
		.form-item {
			margin-bottom: 24rpx;
			.label { display: block; margin-bottom: 10rpx; font-size: 28rpx; color: #333; }
		}
		.current-vehicle { font-size: 30rpx; font-weight: bold; color: #0066CC; }
		.store-seq { font-size: 26rpx; color: #666; line-height: 40rpx; }
		.diff-box {
			background: #f8fbff; padding: 20rpx; border-radius: 10rpx; margin-top: 30rpx;
			.diff-title { font-weight: bold; font-size: 28rpx; display: block; margin-bottom: 10rpx; }
			.diff-row { display: flex; justify-content: space-between; font-size: 26rpx; margin-bottom: 10rpx; color: #666; }
			.highlight { color: #0066CC; font-weight: bold; }
		}
	}
	
	.btn-group {
		display: flex; gap: 20rpx; margin-top: 30rpx;
		button { flex: 1; font-size: 28rpx; }
		.btn-primary { background: #0066CC; color: #fff; }
		.btn-outline { background: #fff; border: 1px solid #ccc; }
	}
	.full-width { width: 100%; margin-top: 20rpx; background: #0066CC; color: #fff; }
}

/* ========== 响应式适配 (Mobile/Tablet) ========== */
@media screen and (max-width: 960px) {
	.main-layout {
		flex-direction: column; /* 垂直排列 */
		padding: 10rpx;
		overflow-y: auto; /* 整体滚动 */
	}

	.layout-left, .layout-center, .layout-right {
		width: 100% !important; /* 强制满宽 */
		flex-shrink: 0;
	}



	/* 移动端地图高度固定 */
	.layout-center {
		height: auto; /* 由 mapHeightCom 控制 */
		order: 2; /* 地图在中间 */
	}

	/* 移动端列表 */
	.layout-right {
		order: 3;
		height: auto;
		.desktop-only { display: none !important; }
		.schedule-item {
			margin-bottom: 16rpx;
			border: 1px solid #eee;
			border-radius: 12rpx;
		}
	}
}
</style>