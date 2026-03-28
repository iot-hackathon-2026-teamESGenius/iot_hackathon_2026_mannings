<template>
	<view class="container">
		<AppNavBar title="车队调度与路径规划" :show-back="true" :show-menu="false" @back="goBack">
			<template #right>
				<view class="nav-btn" @click="openDriverManage">
					<uni-icons type="person" size="20" color="#fff"></uni-icons>
					<text class="btn-text">管理司机</text>
				</view>
			</template>
		</AppNavBar>


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
					<view class="header-actions">
						<button class="add-driver-btn" @click.stop="openAddSchedule">
							<uni-icons type="plusempty" size="14" color="#0066CC"></uni-icons>
							<text>添加调度</text>
						</button>
						<button class="add-driver-btn secondary" @click.stop="openDriverManage">
							<uni-icons type="person" size="14" color="#666"></uni-icons>
							<text>管理司机</text>
						</button>
						<view class="sort-icons">
							<uni-icons type="list" size="20" color="#666" @click.stop="sortList('status')"></uni-icons>
							<uni-icons :type="isListOpen ? 'top' : 'bottom'" size="18" color="#666"></uni-icons>
						</view>
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
								<view class="v-id-row">
									<view class="route-color-dot" :style="{ background: getRouteColor(item.vehicle_id) }"></view>
									<text class="v-id">{{ item.vehicle_id }}</text>
								</view>
								<text class="v-type">{{ item.vehicle_type || 'HGV' }}</text>
							</view>
							<view class="driver-info">
								<text class="name">{{ item.driver_name }}</text>
								<text class="time">出发: {{ item.departure_time }}</text>
								<text class="stores">配送门店: {{ item.store_list.length }}家</text>
								<text v-if="getRouteInfo(item.vehicle_id)" class="route-source">
									{{ formatRouteInfo(getRouteInfo(item.vehicle_id)) }}
								</text>
							</view>
							<view class="status-info">
								<uni-tag :text="formatStatus(item.status)" :type="getStatusType(item.status)" size="small" />
								<text class="cost">HK${{ item.estimated_cost }}</text>
								<button class="mini-adjust" @click.stop="openAdjustModal(item)">调整</button>
																<button class="mini-delete" @click.stop="deleteSchedule(item)">删除</button>
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
						<picker mode="time" :value="adjustForm.departure_time" @change="onDepartureTimeChange">
							<view class="uni-input input-border picker-input">{{ adjustForm.departure_time || '请选择时间' }}</view>
						</picker>
					</view>
					<view class="form-item">
						<text class="label">指派司机</text>
						<uni-data-select v-model="adjustForm.driver_id" :localdata="driverSelectData" placeholder="请选择司机"></uni-data-select>
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

		<!-- 添加调度弹窗 -->
		<uni-popup ref="addSchedulePopup" type="center" :is-mask-click="false">
			<view class="popup-card add-schedule-card">
				<view class="popup-title">
					<text>添加新调度任务</text>
					<uni-icons type="closeempty" size="20" color="#999" @click="$refs.addSchedulePopup.close()"></uni-icons>
				</view>
				
				<view class="schedule-form">
					<view class="form-item">
						<text class="label">车辆编号 <text class="required">*</text></text>
						<uni-easyinput 
							v-model="newSchedule.vehicle_id" 
							placeholder="输入车辆编号，如 V004"
							:clearable="true"
						/>
					</view>
					<view class="form-item">
						<text class="label">车辆类型</text>
						<uni-data-select v-model="newSchedule.vehicle_type" :localdata="vehicleTypeOptions" placeholder="选择车辆类型"></uni-data-select>
					</view>
					<view class="form-item">
						<text class="label">指派司机</text>
						<uni-data-select v-model="newSchedule.driver_id" :localdata="driverSelectData" placeholder="选择司机"></uni-data-select>
					</view>
					<view class="form-item">
						<text class="label">出发时间 <text class="required">*</text></text>
						<picker mode="time" :value="newSchedule.departure_time" @change="onNewDepartureChange">
							<view class="form-input picker-input">{{ newSchedule.departure_time || '请选择时间' }}</view>
						</picker>
					</view>
					<view class="form-item">
						<text class="label">配送门店 <text class="required">*</text></text>
						<view class="store-selector">
							<!-- 搜索框 -->
							<input 
								class="store-search" 
								type="text" 
								v-model="storeSearchKey"
								placeholder="搜索门店..."
							/>
							<!-- 门店列表 -->
							<scroll-view scroll-y class="store-chips">
								<view 
									v-for="store in filteredStores" 
									:key="store.store_code"
									class="store-chip"
									:class="{ selected: newSchedule.store_list.includes(store.store_code) }"
									@click="toggleStoreSelection(store.store_code)"
								>
									<view class="store-main">
										<text class="store-code">{{ store.store_code }}</text>
										<text class="store-name">{{ store.store_name || store.store_code }}</text>
									</view>
									<text v-if="store.district" class="store-district">{{ store.district }}</text>
								</view>
								<view v-if="filteredStores.length === 0" class="no-stores">
									未找到匹配的门店
								</view>
							</scroll-view>
							<view class="store-summary">
								<text class="selected-count">已选: {{ newSchedule.store_list.length }} 家</text>
								<text class="total-count">共 {{ availableStores.length }} 家可选</text>
							</view>
						</view>
					</view>
				</view>
				
				<view class="popup-actions">
					<button class="btn-outline" @click="$refs.addSchedulePopup.close()">取消</button>
					<button class="btn-primary" @click="submitNewSchedule">创建并规划路径</button>
				</view>
			</view>
		</uni-popup>

		<!-- 司机管理弹窗 -->
		<uni-popup ref="driverManagePopup" type="center" :is-mask-click="false">
			<view class="popup-card driver-manage-card">
				<view class="popup-title">
					<text>司机管理</text>
					<view class="title-actions">
						<button class="btn-small btn-primary" @click="showAddDriverForm = !showAddDriverForm">
							{{ showAddDriverForm ? '取消' : '+ 新增' }}
						</button>
					</view>
				</view>
				
				<!-- 新增司机表单 -->
				<view v-if="showAddDriverForm" class="add-driver-form">
					<view class="form-row">
						<input class="form-input" v-model="newDriver.name" placeholder="姓名" />
						<input class="form-input" v-model="newDriver.phone" placeholder="电话" />
					</view>
					<view class="form-row">
						<input class="form-input" v-model="newDriver.license_number" placeholder="驾驶证号" />
						<input class="form-input" v-model="newDriver.vehicle_id" placeholder="车辆ID(如V001)" />
					</view>
					<button class="btn-primary full-width" @click="addNewDriver">确认添加</button>
				</view>
				
				<!-- 司机列表 -->
				<scroll-view scroll-y class="driver-list">
					<view class="driver-list-header">
						<text class="col">姓名</text>
						<text class="col">电话</text>
						<text class="col">车辆</text>
						<text class="col">状态</text>
						<text class="col">操作</text>
					</view>
					<view v-for="driver in driverList" :key="driver.driver_id" class="driver-item">
						<text class="col name">{{ driver.name }}</text>
						<text class="col">{{ driver.phone }}</text>
						<text class="col vehicle">{{ driver.vehicle_id || '-' }}</text>
						<view class="col">
							<uni-tag :text="formatDriverStatus(driver.status)" :type="getDriverStatusType(driver.status)" size="small" />
						</view>
						<view class="col actions">
							<text class="action-btn" @click="editDriver(driver)">编辑</text>
							<text class="action-btn delete" @click="deleteDriver(driver)">删除</text>
						</view>
					</view>
					<view v-if="driverList.length === 0" class="empty-tip">暂无司机数据</view>
				</scroll-view>
				
				<view class="driver-stats">
					<text>可用: {{ driverStats.available }}</text>
					<text>值班: {{ driverStats.on_duty }}</text>
					<text>休息: {{ driverStats.off_duty }}</text>
				</view>
				
				<button class="btn-outline full-width" @click="$refs.driverManagePopup.close()">关闭</button>
			</view>
		</uni-popup>

	</view>
</template>

<script>

import { apiGet, apiPut, apiPost, apiDelete } from '../../utils/api.js'
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
			isTracking: true, // 是否开启实时追踪（默认开启）
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

			// 路线颜色配置
			routeColors: [
				'#E63946', // 鲜红 - 醒目
				'#2D6A4F', // 深绿 - 与地图浅绿区分
				'#7B2CBF', // 紫色 - 独特
				'#F77F00', // 橙色 - 醒目
				'#0077B6', // 深蓝 - 与浅蓝水域区分
				'#D62828', // 暗红 - 备用
				'#9D4EDD', // 浅紫 - 备用
				'#06D6A0'  // 青绿 - 备用
			],

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
			},
			
			// 5. 司机管理数据
			driverList: [],
			driverStats: { available: 0, on_duty: 0, off_duty: 0 },
			showAddDriverForm: false,
			newDriver: {
				name: '',
				phone: '',
				license_number: '',
				vehicle_id: ''
			},
			
			// 新调度任务表单
			newSchedule: {
				vehicle_id: '',
				vehicle_type: 'HGV',
				driver_id: '',
				departure_time: '',
				store_list: []
			},
			
			// 车辆类型选项
			vehicleTypeOptions: [
				{ value: 'HGV', text: 'HGV - 重型货车' },
				{ value: 'LGV', text: 'LGV - 轻型货车' },
				{ value: 'VAN', text: 'VAN - 厂车' }
			],
			
			// 可选门店列表
			availableStores: [],
			
			// 门店搜索关键词
			storeSearchKey: ''
		}
	},
	computed: {
		// 过滤后的门店列表
		filteredStores() {
			if (!this.storeSearchKey) {
				return this.availableStores
			}
			const key = this.storeSearchKey.toLowerCase()
			return this.availableStores.filter(store => {
				const name = (store.store_name || '').toLowerCase()
				const code = (store.store_code || '').toLowerCase()
				const district = (store.district || '').toLowerCase()
				return name.includes(key) || code.includes(key) || district.includes(key)
			})
		},
		
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
		// 将 scheduleList 转换为下拉框数据
		vehicleSelectData() {
			return this.scheduleList.map(item => ({
				value: item.vehicle_id,
				text: `${item.vehicle_id} - ${item.driver_name}`
			}))
		},
		// 司机下拉框数据
		driverSelectData() {
			return this.driverList.map(driver => ({
				value: driver.driver_id,
				text: `${driver.name}${driver.vehicle_id ? ' (' + driver.vehicle_id + ')' : ''}`
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
		this.fetchDrivers() // 加载司机数据
		
		// 启动实时追踪
		this.startRealtimeTracking()
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
				const res = await apiGet('/planning/schedules')
				if (res && res.success) {
					this.scheduleList = res.data.schedules || []
					
					// 合并本地存储的自定义调度
					const localSchedules = this.loadLocalSchedules()
					if (localSchedules.length > 0) {
						// 过滤掉已存在的（以vehicle_id为准）
						const existingIds = new Set(this.scheduleList.map(s => s.vehicle_id))
						const newLocalSchedules = localSchedules.filter(s => !existingIds.has(s.vehicle_id))
						this.scheduleList = [...this.scheduleList, ...newLocalSchedules]
					}
					
					// 获取列表后，加载地图上的门店/DC和默认路线（cachedRoutes）
					await this.fetchMapData()
					
					// 恢复本地存储的路线（新添加的调度路线）
					// 注意：优先使用API返回的真实路径，只有当API没有返回时才使用本地存储的路线
					const localRoutes = this.loadLocalRoutes()
					if (localRoutes.length > 0) {
						for (const localRoute of localRoutes) {
							const exists = this.cachedRoutes.some(r => r.vehicle_id === localRoute.vehicle_id)
							if (!exists) {
								// 检查本地路线是否是直线路径，如果是则尝试重新获取真实路径
								if (localRoute.source === 'direct') {
									console.log(`本地路线 ${localRoute.vehicle_id} 是直线路径，尝试重新获取真实路径`)
									// 重新调用API获取真实路径
									try {
										const routePayload = {
											vehicle_id: localRoute.vehicle_id,
											store_ids: localRoute.store_ids || [],
											optimize: true
										}
										const routeRes = await apiPost('/planning/routes/optimize', routePayload)
										if (routeRes && routeRes.success && routeRes.data) {
											this.cachedRoutes.push({
												vehicle_id: localRoute.vehicle_id,
												coordinates: routeRes.data.coordinates,
												distance_meters: routeRes.data.distance_meters,
												duration_seconds: routeRes.data.duration_seconds,
												source: routeRes.data.source,
												store_ids: routeRes.data.store_ids
											})
											console.log(`成功为 ${localRoute.vehicle_id} 获取真实路径`)
											continue
										}
									} catch (e) {
										console.warn(`重新获取路线失败: ${e}`)
									}
								}
								// 如果无法重新获取，使用本地路线
								this.cachedRoutes.push(localRoute)
							}
						}
						console.log(`处理了 ${localRoutes.length} 条本地路线`)
					}
					
					// 同步获取一次实时位置以标注车辆
					await this.fetchRealTimePositions()
				}
			} catch (e) {
				console.error('获取调度列表失败', e)
				// 尝试加载本地数据
				this.scheduleList = this.loadLocalSchedules()
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
							const colorIdx = this.cachedRoutes.findIndex(r => r.vehicle_id === selected)
							this.mapPolylines = [{ points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: this.routeColors[colorIdx % this.routeColors.length], width: 4 }]
						}
					} else {
						// 没有选中车辆时，显示所有路线
						this.mapPolylines = this.cachedRoutes.map((route, idx) => ({
							points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })),
							color: this.routeColors[idx % this.routeColors.length],
							width: 3,
							dottedLine: false,
							arrowLine: true
						}))
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
		
		// 启动实时追踪
		startRealtimeTracking() {
			if (this.timer) return // 避免重复启动
			this.fetchRealTimePositions() // 立即执行一次
			this.timer = setInterval(() => {
				this.fetchRealTimePositions()
			}, 3000) // 每3秒更新
		},

		// API 4: 调整调度方案
		openAdjustModal(item) {
			// 从"明细列表每行按钮"进入：预填充该车信息
			if (item && item.vehicle_id) {
				this.adjustForm.vehicle_id = item.vehicle_id
				this.adjustForm.departure_time = item.departure_time || '08:00'
				// 后端字段是 driver_id，这里先用现有的 driver_name 兜底展示（如后端补充 driver_id 可直接替换）
				this.adjustForm.driver_id = item.driver_id || item.driver_name || ''
				this.adjustForm.store_list = Array.isArray(item.store_list) ? item.store_list : []
			}
			this.$refs.adjustPopup.open()
		},
				
		// 时间选择器变更
		onDepartureTimeChange(e) {
			this.adjustForm.departure_time = e.detail.value
		},
		async submitAdjustment() {
			if (!this.adjustForm.vehicle_id) return uni.showToast({title:'请选择车辆', icon:'none'})
			
			const vehicleId = this.adjustForm.vehicle_id
			const payload = {
				departure_time: this.adjustForm.departure_time,
				driver_id: this.adjustForm.driver_id,
				operator: 'Admin', // 当前用户
			}
			
			// 先本地更新，确保立即反映
			const idx = this.scheduleList.findIndex(s => s.vehicle_id === vehicleId)
			if (idx >= 0) {
				// 更新出发时间
				if (payload.departure_time) {
					this.scheduleList[idx].departure_time = payload.departure_time
				}
				// 更新司机
				if (payload.driver_id) {
					const driver = this.driverList.find(d => d.driver_id === payload.driver_id)
					this.scheduleList[idx].driver_id = payload.driver_id
					this.scheduleList[idx].driver_name = driver ? driver.name : this.scheduleList[idx].driver_name
				}
			}

			try {
				await apiPut(`/planning/schedules/${vehicleId}/adjust`, payload)
				uni.showToast({ title: '调整方案已提交', icon: 'success' })
			} catch (e) {
				// API失败，但本地已更新
				uni.showToast({ title: '本地已更新', icon: 'success' })
			}
			
			this.$refs.adjustPopup.close()
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
				// 选中车辆时同时展示对应路线（使用对应颜色）
				const routeIdx = this.cachedRoutes.findIndex(r => r.vehicle_id === marker.entity)
				const route = this.cachedRoutes[routeIdx]
				if (route && route.coordinates) {
					const color = this.routeColors[routeIdx % this.routeColors.length]
					this.mapPolylines = [{ points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: color, width: 5 }]
				}
			}
		},

		async focusVehicle(item) {
			this.currentVehicleId = item.vehicle_id

			// 找到对应 route（优先使用已缓存的 route）
			let routeIdx = this.cachedRoutes.findIndex(r => r.vehicle_id === item.vehicle_id)
			let route = routeIdx >= 0 ? this.cachedRoutes[routeIdx] : null
			
			// 如果找不到路线，先从本地存储查找
			if (!route) {
				const localRoutes = this.loadLocalRoutes()
				const localRoute = localRoutes.find(r => r.vehicle_id === item.vehicle_id)
				if (localRoute) {
					// 添加到缓存
					this.cachedRoutes.push(localRoute)
					routeIdx = this.cachedRoutes.length - 1
					route = localRoute
				}
			}
			
			// 如果还是找不到，调用fetchMapData
			if (!route) {
				// 保存当前所有本地路线
				const existingLocalRoutes = this.cachedRoutes.filter(r => r.source === 'amap' || r.source === 'direct')
				
				await this.fetchMapData()
				
				// 合并本地路线
				for (const lr of existingLocalRoutes) {
					const exists = this.cachedRoutes.some(r => r.vehicle_id === lr.vehicle_id)
					if (!exists) {
						this.cachedRoutes.push(lr)
					}
				}
				
				routeIdx = this.cachedRoutes.findIndex(r => r.vehicle_id === item.vehicle_id)
				route = routeIdx >= 0 ? this.cachedRoutes[routeIdx] : null
			}

			if (route && route.coordinates && route.coordinates.length > 0) {
				const color = this.routeColors[routeIdx % this.routeColors.length]
				this.mapPolylines = [ { points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })), color: color, width: 5 } ]
				
				// 添加途经门店标记
				await this.addStoreMarkersForRoute(item, color)
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
		
		// 删除调度
		deleteSchedule(item) {
			uni.showModal({
				title: '确认删除',
				content: `确定要删除调度 ${item.vehicle_id} 吗？`,
				success: (res) => {
					if (res.confirm) {
						// 从列表中删除
						const idx = this.scheduleList.findIndex(s => s.vehicle_id === item.vehicle_id)
						if (idx >= 0) {
							this.scheduleList.splice(idx, 1)
						}
						
						// 从缓存路线中删除
						const routeIdx = this.cachedRoutes.findIndex(r => r.vehicle_id === item.vehicle_id)
						if (routeIdx >= 0) {
							this.cachedRoutes.splice(routeIdx, 1)
						}
						
						// 从本地存储中删除
						let localSchedules = this.loadLocalSchedules()
						localSchedules = localSchedules.filter(s => s.vehicle_id !== item.vehicle_id)
						this.saveLocalSchedules(localSchedules)
						
						let localRoutes = this.loadLocalRoutes()
						localRoutes = localRoutes.filter(r => r.vehicle_id !== item.vehicle_id)
						this.saveLocalRoutes(localRoutes)
						
						// 如果删除的是当前选中的车辆，清除选中状态
						if (this.currentVehicleId === item.vehicle_id) {
							this.currentVehicleId = null
							// 显示所有路线
							this.mapPolylines = this.cachedRoutes.map((route, idx) => ({
								points: route.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })),
								color: this.routeColors[idx % this.routeColors.length],
								width: 3,
								arrowLine: true
							}))
						}
						
						uni.showToast({ title: '删除成功', icon: 'success' })
					}
				}
			})
		},
		
		// 为路线添加途经门店标记
		async addStoreMarkersForRoute(item, color) {
			// 获取该调度的门店列表
			const storeList = item.store_list || []
			if (storeList.length === 0) return
			
			// 优先使用调度中保存的门店详情
			let storeDetails = item.store_details || []
			
			// 如果没有门店详情，从 API 获取
			if (storeDetails.length === 0) {
				try {
					const res = await apiGet('/planning/stores')
					if (res && res.success && res.data) {
						const allStores = res.data.stores || res.data
						storeDetails = storeList.map(storeId => {
							const found = allStores.find(s => s.store_id === storeId || s.store_code === storeId)
							return found ? { 
								store_code: found.store_id,
								store_name: found.name,
								lat: found.lat,
								lng: found.lng
							} : null
						}).filter(s => s && s.lat && s.lng)
					}
				} catch (e) {
					console.warn('获取门店详情失败', e)
				}
			}
			
			// 移除旧的门店标记（保留 DC 和车辆标记）
			this.mapMarkers = this.mapMarkers.filter(m => 
				m.entity === 'DC' || 
				(m.entity && m.entity.startsWith && m.entity.startsWith('V')) ||
				m.customType !== 'route-store'
			)
			
			// 添加新的门店标记
			for (let i = 0; i < storeDetails.length; i++) {
				const store = storeDetails[i]
				if (!store.lat || !store.lng) continue
				
				const marker = {
					id: this.getNextMarkerId(),
					entity: store.store_code || store.store_id,
					latitude: store.lat,
					longitude: store.lng,
					width: 28,
					height: 28,
					iconPath: '/static/img/store.png',
					customType: 'route-store',
					callout: {
						content: `${i + 1}. ${store.store_name || store.store_code}`,
						color: '#ffffff',
						fontSize: 12,
						borderRadius: 6,
						bgColor: color,
						padding: 6,
						display: 'ALWAYS'
					},
					label: {
						content: String(i + 1),
						color: '#ffffff',
						fontSize: 12,
						bgColor: color,
						padding: 4,
						borderRadius: 10,
						anchorX: -8,
						anchorY: -8
					}
				}
				this.mapMarkers.push(marker)
			}
			
			// 确保 DC 标记存在
			const dcMarker = this.mapMarkers.find(m => m.entity === 'DC')
			if (!dcMarker) {
				this.mapMarkers.push({
					id: this.getNextMarkerId(),
					entity: 'DC',
					latitude: 22.3700,
					longitude: 114.1130,
					width: 34,
					height: 34,
					iconPath: '/static/img/DC.png',
					callout: {
						content: '配送中心 (DC)',
						color: '#ffffff',
						fontSize: 14,
						borderRadius: 6,
						bgColor: '#2e7d32',
						padding: 8,
						display: 'ALWAYS'
					}
				})
			}
		},

		// Helper: generate next numeric marker id
		getNextMarkerId() {
			this.markerIdCounter = (this.markerIdCounter || 1000) + 1
			return this.markerIdCounter
		},
		
		// ==================== 司机管理方法 ====================
		
		async fetchDrivers() {
			try {
				const res = await apiGet('/drivers/list')
				if (res && res.success && res.data) {
					this.driverList = res.data.drivers || []
					this.driverStats = res.data.statistics || { available: 0, on_duty: 0, off_duty: 0 }
				}
			} catch (e) {
				console.error('获取司机列表失败', e)
			}
		},
		
		// ========== 本地存储管理 ==========
		loadLocalSchedules() {
			try {
				const stored = uni.getStorageSync('custom_schedules')
				return stored ? JSON.parse(stored) : []
			} catch (e) {
				return []
			}
		},
		
		saveLocalSchedules(schedules) {
			try {
				uni.setStorageSync('custom_schedules', JSON.stringify(schedules))
			} catch (e) {
				console.error('保存本地调度失败', e)
			}
		},
		
		// 保存本地路线数据
		saveLocalRoutes(routes) {
			try {
				uni.setStorageSync('custom_routes', JSON.stringify(routes))
			} catch (e) {
				console.error('保存本地路线失败', e)
			}
		},
		
		// 加载本地路线数据
		loadLocalRoutes() {
			try {
				const stored = uni.getStorageSync('custom_routes')
				return stored ? JSON.parse(stored) : []
			} catch (e) {
				return []
			}
		},
		
		// ========== 添加调度任务 ==========
				async openAddSchedule() {
					// 加载可选门店
					await this.fetchAvailableStores()
					// 重置表单
					this.newSchedule = {
						vehicle_id: this.generateNextVehicleId(),
						vehicle_type: 'HGV',
						driver_id: '',
						departure_time: '',
						store_list: []
					}
					this.$refs.addSchedulePopup.open()
				},
				
				// 生成下一个车辆ID
				generateNextVehicleId() {
					const existingIds = this.scheduleList.map(s => s.vehicle_id)
					for (let i = 1; i <= 99; i++) {
						const id = `V${String(i).padStart(3, '0')}`
						if (!existingIds.includes(id)) return id
					}
					return `V${Date.now().toString().slice(-3)}`
				},
				
				// 加载可选门店（使用真实门店数据）
				async fetchAvailableStores() {
					try {
						// 使用 planning 路由的门店列表（包含经纬度）
						const res = await apiGet('/planning/stores')
						console.log('门店API响应:', res)
						
						if (res && res.success && res.data) {
							const storeData = res.data.stores || res.data
							
							// 过滤掉已被分配的门店
							const assignedStores = new Set()
							this.scheduleList.forEach(s => {
								if (s.store_list) s.store_list.forEach(st => assignedStores.add(st))
							})
							
							this.availableStores = storeData
								.filter(store => {
									const storeId = store.store_id || store.store_code
									return !assignedStores.has(storeId)
								})
								.map(store => ({
									store_code: store.store_id || store.store_code,
									store_name: store.name || store.store_name || `Mannings ${store.district}`,
									district: store.district,
									lat: store.lat,
									lng: store.lng
								}))
							console.log(`加载了 ${this.availableStores.length} 个可选门店`)
							return
						}
						
						// 备选：尝试公开门店API
						const publicRes = await apiGet('/stores/public')
						if (publicRes && publicRes.data) {
							this.availableStores = publicRes.data.map(store => ({
								store_code: store.store_id,
								store_name: store.store_name || `Mannings ${store.district}`,
								district: store.district
							}))
							console.log(`从公开API加载了 ${this.availableStores.length} 个门店`)
							return
						}
						
						throw new Error('No store data from APIs')
					} catch (e) {
						console.warn('获取真实门店失败，使用备用数据', e)
						// 备用数据 - 使用香港常见地区
						this.availableStores = [
							{ store_code: 'MN001', store_name: 'Mannings 尖沙咀', district: '油尖旺', lat: 22.2988, lng: 114.1722 },
							{ store_code: 'MN002', store_name: 'Mannings 旺角', district: '油尖旺', lat: 22.3193, lng: 114.1694 },
							{ store_code: 'MN003', store_name: 'Mannings 铜锣湾', district: '港岛', lat: 22.2800, lng: 114.1819 },
							{ store_code: 'MN004', store_name: 'Mannings 观塘', district: '观塘', lat: 22.3111, lng: 114.2253 },
							{ store_code: 'MN005', store_name: 'Mannings 沙田', district: '沙田', lat: 22.3814, lng: 114.1873 },
							{ store_code: 'MN006', store_name: 'Mannings 大埔', district: '大埔', lat: 22.4513, lng: 114.1644 },
							{ store_code: 'MN007', store_name: 'Mannings 元朗', district: '元朗', lat: 22.4445, lng: 114.0224 },
							{ store_code: 'MN008', store_name: 'Mannings 屯门', district: '屯门', lat: 22.3908, lng: 113.9758 }
						]
					}
				},
				
				// 切换门店选择
				toggleStoreSelection(storeCode) {
					const idx = this.newSchedule.store_list.indexOf(storeCode)
					if (idx >= 0) {
						this.newSchedule.store_list.splice(idx, 1)
					} else {
						this.newSchedule.store_list.push(storeCode)
					}
				},
				
				// 新调度出发时间变化
				onNewDepartureChange(e) {
					this.newSchedule.departure_time = e.detail.value
				},
				
				// 提交新调度
				async submitNewSchedule() {
					const { vehicle_id, departure_time, store_list } = this.newSchedule
					
					if (!vehicle_id) return uni.showToast({ title: '请输入车辆编号', icon: 'none' })
					if (!departure_time) return uni.showToast({ title: '请选择出发时间', icon: 'none' })
					if (store_list.length === 0) return uni.showToast({ title: '请至少选择一个门店', icon: 'none' })
					
					// 检查车辆ID是否已存在
					if (this.scheduleList.some(s => s.vehicle_id === vehicle_id)) {
						return uni.showToast({ title: '车辆编号已存在', icon: 'none' })
					}
					
					uni.showLoading({ title: '创建并规划路径中...' })
					
					try {
						// 查找司机信息
						const driver = this.driverList.find(d => d.driver_id === this.newSchedule.driver_id)
						
						// 获取选中门店的详细信息
						const selectedStores = this.availableStores.filter(s => store_list.includes(s.store_code))
						
						const payload = {
							vehicle_id: vehicle_id,
							vehicle_type: this.newSchedule.vehicle_type,
							driver_id: this.newSchedule.driver_id,
							driver_name: driver ? driver.name : '待分配',
							departure_time: departure_time,
							store_list: [...store_list],
							store_details: selectedStores, // 保存门店详情用于路径规划
							status: 'pending',
							estimated_cost: Math.round(50 + store_list.length * 25 + Math.random() * 50),
							created_at: new Date().toISOString()
						}
						
						// 本地添加到列表
						this.scheduleList.push(payload)
						
						// 保存到本地存储（确保刷新后不丢失）
						const localSchedules = this.loadLocalSchedules()
						localSchedules.push(payload)
						this.saveLocalSchedules(localSchedules)
						
						// 调用路径规划API并添加新路线
						try {
							const routePayload = {
								vehicle_id: vehicle_id,
								store_ids: store_list,
								optimize: true
							}
							const routeRes = await apiPost('/planning/routes/optimize', routePayload)
							console.log('路径规划结果:', routeRes)
							
							if (routeRes && routeRes.success && routeRes.data) {
								// 将新路线添加到缓存
								const newRoute = {
									vehicle_id: vehicle_id,
									coordinates: routeRes.data.coordinates,
									distance_meters: routeRes.data.distance_meters,
									duration_seconds: routeRes.data.duration_seconds,
									source: routeRes.data.source,
									store_ids: routeRes.data.store_ids
								}
								this.cachedRoutes.push(newRoute)
								
								// 立即显示新路线（使用新的颜色）
								const routeIdx = this.cachedRoutes.length - 1
								const color = this.routeColors[routeIdx % this.routeColors.length]
								
								// 添加新路线到地图
								const newPolyline = {
									points: newRoute.coordinates.map(c => ({ latitude: c[0], longitude: c[1] })),
									color: color,
									width: 4,
									arrowLine: true
								}
								this.mapPolylines = [...this.mapPolylines, newPolyline]
								
								// 添加门店标记
								for (const store of selectedStores) {
									if (store.lat && store.lng) {
										const marker = {
											id: this.getNextMarkerId(),
											entity: store.store_code,
											latitude: store.lat,
											longitude: store.lng,
											width: 22,
											height: 22,
											callout: { content: store.store_name },
											label: { content: 'S', color: '#fff', bgColor: color, padding: 6, borderRadius: 6 }
										}
										this.mapMarkers = [...this.mapMarkers, marker]
									}
								}
								
								console.log(`新路线已添加，颜色: ${color}`)
								
								// 保存本地路线到存储
								const localRoutes = this.loadLocalRoutes()
								localRoutes.push(newRoute)
								this.saveLocalRoutes(localRoutes)
							}
						} catch (routeErr) {
							console.warn('路径规划API调用失败', routeErr)
							// 尝试使用门店坐标生成直线路径
							if (selectedStores.length > 0) {
								const dcLoc = { lat: 22.3700, lng: 114.1130 }
								const coordinates = [[dcLoc.lat, dcLoc.lng]]
								for (const store of selectedStores) {
									if (store.lat && store.lng) {
										coordinates.push([store.lat, store.lng])
									}
								}
								coordinates.push([dcLoc.lat, dcLoc.lng])
								
								const newRoute = {
									vehicle_id: vehicle_id,
									coordinates: coordinates,
									source: 'direct'
								}
								this.cachedRoutes.push(newRoute)
								
								const routeIdx = this.cachedRoutes.length - 1
								const color = this.routeColors[routeIdx % this.routeColors.length]
								
								this.mapPolylines = [...this.mapPolylines, {
									points: coordinates.map(c => ({ latitude: c[0], longitude: c[1] })),
									color: color,
									width: 4,
									dottedLine: true
								}]
								
								// 保存本地路线到存储
								const localRoutes = this.loadLocalRoutes()
								localRoutes.push(newRoute)
								this.saveLocalRoutes(localRoutes)
							}
						}
						
						uni.showToast({ title: '调度创建成功', icon: 'success' })
						this.$refs.addSchedulePopup.close()
						
						// 聚焦到新车辆
						const newItem = this.scheduleList.find(s => s.vehicle_id === vehicle_id)
						if (newItem) {
							this.focusVehicle(newItem)
						}
					} catch (e) {
						uni.showToast({ title: '创建失败', icon: 'none' })
					} finally {
						uni.hideLoading()
					}
				},
				
				// ========== 司机管理 ==========
				openDriverManage() {
			this.fetchDrivers()
			this.$refs.driverManagePopup.open()
		},
		
		async addNewDriver() {
			if (!this.newDriver.name || !this.newDriver.phone) {
				return uni.showToast({ title: '请填写姓名和电话', icon: 'none' })
			}
			
			try {
				const res = await apiPost('/drivers/create', this.newDriver)
				if (res && res.success) {
					uni.showToast({ title: '添加成功', icon: 'success' })
					this.showAddDriverForm = false
					this.newDriver = { name: '', phone: '', license_number: '', vehicle_id: '' }
					await this.fetchDrivers()
				}
			} catch (e) {
				uni.showToast({ title: '添加失败', icon: 'none' })
			}
		},
		
		editDriver(driver) {
			// 简化编辑：使用弹窗输入新车辆ID
			uni.showModal({
				title: `编辑司机: ${driver.name}`,
				editable: true,
				placeholderText: '输入新车辆ID（如V001）',
				success: async (res) => {
					if (res.confirm && res.content) {
						try {
							await apiPut(`/drivers/${driver.driver_id}`, { vehicle_id: res.content })
							uni.showToast({ title: '更新成功', icon: 'success' })
							await this.fetchDrivers()
						} catch (e) {
							uni.showToast({ title: '更新失败', icon: 'none' })
						}
					}
				}
			})
		},
		
		async deleteDriver(driver) {
			uni.showModal({
				title: '确认删除',
				content: `确定要删除司机 "${driver.name}" 吗？`,
				success: async (res) => {
					if (res.confirm) {
						try {
							await apiDelete(`/drivers/${driver.driver_id}`)
							uni.showToast({ title: '删除成功', icon: 'success' })
							await this.fetchDrivers()
						} catch (e) {
							uni.showToast({ title: '删除失败', icon: 'none' })
						}
					}
				}
			})
		},
		
		formatDriverStatus(status) {
			const map = { available: '可用', on_duty: '值班', off_duty: '休息' }
			return map[status] || status
		},
		
		getDriverStatusType(status) {
			const map = { available: 'success', on_duty: 'primary', off_duty: 'default' }
			return map[status] || 'default'
		},
		
		// 获取路径信息
		getRouteInfo(vehicleId) {
			const route = this.cachedRoutes.find(r => r.vehicle_id === vehicleId)
			return route?.route_info || null
		},
		
		// 获取路线颜色
		getRouteColor(vehicleId) {
			const idx = this.cachedRoutes.findIndex(r => r.vehicle_id === vehicleId)
			if (idx >= 0) {
				return this.routeColors[idx % this.routeColors.length]
			}
			// 默认根据 vehicle_id 的索引生成颜色
			const schedIdx = this.scheduleList.findIndex(s => s.vehicle_id === vehicleId)
			return this.routeColors[schedIdx >= 0 ? schedIdx % this.routeColors.length : 0]
		},
		
		// 格式化路径信息
		formatRouteInfo(info) {
			if (!info) return ''
			const source = {
				'amap': '🛣️ 高德地图',
				'google': '🛣️ 谷歌地图',
				'fallback': '🛣️ 模拟路径',
				'direct': '—— 直线'
			}[info.source] || info.source
			
			if (info.distance_meters > 0) {
				const km = (info.distance_meters / 1000).toFixed(1)
				const min = Math.round(info.duration_seconds / 60)
				return `${source} ${km}km/${min}分钟`
			}
			return source
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
			
			.header-actions {
				display: flex;
				align-items: center;
				gap: 16rpx;
			}
			
			.add-driver-btn {
				display: flex;
				align-items: center;
				gap: 6rpx;
				padding: 8rpx 16rpx;
				background: #e8f4fd;
				border: 1px solid #0066CC;
				border-radius: 8rpx;
				font-size: 22rpx;
				color: #0066CC;
				
				&:active {
					background: #d0e8f9;
				}
			}
			
			.sort-icons {
				display: flex;
				align-items: center;
				gap: 8rpx;
			}
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
		width: 480rpx;
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
				gap: 16rpx;
				
				.vehicle-info {
					display: flex; flex-direction: column;
					width: 90rpx;
					flex-shrink: 0;
					.v-id-row {
						display: flex;
						align-items: center;
						gap: 6rpx;
					}
					.route-color-dot {
						width: 16rpx;
						height: 16rpx;
						border-radius: 50%;
						flex-shrink: 0;
					}
					.v-id { font-weight: bold; color: #333; font-size: 26rpx; }
					.v-type { font-size: 20rpx; color: #999; background: #f5f5f5; padding: 2rpx 8rpx; border-radius: 4rpx; width: fit-content; margin-top: 6rpx; }
				}
				.driver-info {
					display: flex; flex-direction: column;
					flex: 1;
					min-width: 120rpx;
					overflow: hidden;
					.name { font-size: 28rpx; color: #333; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
					.time { font-size: 24rpx; color: #666; margin-top: 6rpx; white-space: nowrap; }
					.stores { font-size: 24rpx; color: #999; white-space: nowrap; }
					.route-source { 
						font-size: 20rpx; 
						color: #0066CC; 
						background: #e8f4fd;
						padding: 4rpx 10rpx;
						border-radius: 6rpx;
						margin-top: 6rpx;
						width: fit-content;
						max-width: 100%;
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
					}
				}
				.status-info {
					display: flex; flex-direction: column; align-items: flex-end;
					width: 100rpx;
					flex-shrink: 0;
					.cost { font-size: 24rpx; color: #666; margin-top: 10rpx; white-space: nowrap; }
					.mini-adjust {
						margin-top: 12rpx;
						height: 52rpx;
						line-height: 52rpx;
						padding: 0 16rpx;
						font-size: 22rpx;
						background: #e8f4fd;
						color: #0066CC;
					}
					
					.mini-delete {
						margin-top: 8rpx;
						height: 52rpx;
						line-height: 52rpx;
						padding: 0 16rpx;
						font-size: 22rpx;
						background: #ffe6e6;
						color: #dc3545;
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
		.picker-input { 
			color: #333; 
			cursor: pointer;
			background: #f8f9fa;
		}
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

/* 导航栏右侧按钮 */
.nav-btn {
	display: flex;
	align-items: center;
	gap: 8rpx;
	padding: 12rpx 24rpx;
	background: rgba(255,255,255,0.25);
	border-radius: 8rpx;
	border: 1px solid rgba(255,255,255,0.4);
	
	&:active {
		background: rgba(255,255,255,0.4);
	}
	
	.btn-text {
		font-size: 26rpx;
		color: #fff;
		font-weight: 500;
	}
}

/* 司机管理弹窗 */
/* 添加调度弹窗 */
.add-schedule-card {
	width: 90vw;
	max-width: 800rpx;
	max-height: 85vh;
	
	.popup-title {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 20rpx;
		border-bottom: 1px solid #eee;
		margin-bottom: 20rpx;
	}
	
	.schedule-form {
		max-height: 55vh;
		padding: 10rpx 0;
	}
	
	.form-item {
		margin-bottom: 24rpx;
		
		.label {
			display: block;
			font-size: 26rpx;
			color: #333;
			margin-bottom: 12rpx;
			
			.required {
				color: #E63946;
			}
		}
		
		.form-input {
			width: 100%;
			padding: 20rpx 24rpx;
			border: 1px solid #ddd;
			border-radius: 8rpx;
			font-size: 30rpx;
			color: #333;
			box-sizing: border-box;
			background: #fff;
			
			&.picker-input {
				background: #fafafa;
				color: #333;
			}
		}
	}
	
	.store-selector {
		.store-search {
			width: 100%;
			padding: 16rpx 20rpx;
			border: 1px solid #ddd;
			border-radius: 8rpx;
			font-size: 28rpx;
			margin-bottom: 16rpx;
			background: #fff;
		}
		
		.store-chips {
			height: 320rpx;
			padding: 12rpx;
			background: #fafafa;
			border-radius: 8rpx;
			border: 1px solid #eee;
		}
		
		.store-chip {
			display: flex;
			justify-content: space-between;
			align-items: center;
			padding: 16rpx 20rpx;
			margin-bottom: 12rpx;
			background: #fff;
			border: 1px solid #ddd;
			border-radius: 8rpx;
			transition: all 0.2s;
			
			.store-main {
				display: flex;
				align-items: center;
				gap: 12rpx;
				flex: 1;
			}
			
			.store-code {
				font-size: 22rpx;
				color: #0066CC;
				background: #e8f4fd;
				padding: 4rpx 12rpx;
				border-radius: 6rpx;
				font-weight: 500;
			}
			
			.store-name {
				font-size: 26rpx;
				color: #333;
			}
			
			.store-district {
				font-size: 22rpx;
				color: #999;
				margin-left: 16rpx;
				flex-shrink: 0;
			}
			
			&.selected {
				background: #0066CC;
				border-color: #0066CC;
				
				.store-code {
					background: rgba(255,255,255,0.2);
					color: #fff;
				}
				
				.store-name, .store-district {
					color: #fff;
				}
			}
			
			&:active {
				opacity: 0.8;
			}
		}
		
		.no-stores {
			text-align: center;
			padding: 40rpx;
			color: #999;
			font-size: 26rpx;
		}
		
		.store-summary {
			display: flex;
			justify-content: space-between;
			margin-top: 16rpx;
			
			.selected-count {
				font-size: 26rpx;
				color: #0066CC;
				font-weight: 500;
			}
			
			.total-count {
				font-size: 24rpx;
				color: #999;
			}
		}
	}
	
	.popup-actions {
		display: flex;
		gap: 20rpx;
		margin-top: 30rpx;
		padding-top: 20rpx;
		border-top: 1px solid #eee;
		
		button {
			flex: 1;
		}
	}
}

/* 添加调度按钮样式 */
.add-driver-btn.secondary {
	background: #f5f5f5;
	border-color: #ddd;
	color: #666;
	
	&:active {
		background: #eee;
	}
}

/* 司机管理弹窗 */
.driver-manage-card {
	width: 720rpx;
	max-height: 80vh;
	
	.popup-title {
		display: flex;
		justify-content: space-between;
		align-items: center;
		
		.title-actions {
			.btn-small {
				height: 56rpx;
				line-height: 56rpx;
				padding: 0 24rpx;
				font-size: 24rpx;
			}
		}
	}
	
	.add-driver-form {
		background: #f8f9fa;
		padding: 20rpx;
		border-radius: 12rpx;
		margin-bottom: 20rpx;
		
		.form-row {
			display: flex;
			gap: 16rpx;
			margin-bottom: 16rpx;
			
			.form-input {
				flex: 1;
				height: 72rpx;
				padding: 0 20rpx;
				border: 1px solid #ddd;
				border-radius: 8rpx;
				background: #fff;
				font-size: 26rpx;
			}
		}
	}
	
	.driver-list {
		max-height: 400rpx;
		margin-bottom: 20rpx;
		
		.driver-list-header {
			display: flex;
			padding: 16rpx 0;
			border-bottom: 2rpx solid #eee;
			background: #f8f9fa;
			
			.col {
				flex: 1;
				font-size: 24rpx;
				color: #666;
				text-align: center;
			}
		}
		
		.driver-item {
			display: flex;
			align-items: center;
			padding: 20rpx 0;
			border-bottom: 1px solid #f0f0f0;
			
			.col {
				flex: 1;
				font-size: 26rpx;
				text-align: center;
				
				&.name { font-weight: bold; color: #333; }
				&.vehicle { color: #0066CC; }
				
				&.actions {
					display: flex;
					justify-content: center;
					gap: 16rpx;
					
					.action-btn {
						color: #0066CC;
						font-size: 24rpx;
						
						&.delete { color: #dc3545; }
					}
				}
			}
		}
	}
	
	.driver-stats {
		display: flex;
		justify-content: space-around;
		padding: 20rpx;
		background: #e8f4fd;
		border-radius: 8rpx;
		margin-bottom: 20rpx;
		
		text {
			font-size: 26rpx;
			color: #0066CC;
		}
	}
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