<template>
	<view class="container">
		<AppNavBar title="演示控制台" :show-back="true" :show-menu="false" @back="goBack" />

		<scroll-view scroll-y class="main-content">
			<!-- 系统状态卡片 -->
			<view class="status-card">
				<view class="status-header">
					<text class="status-title">万宁门店取货SLA优化系统</text>
					<view class="status-badge" :class="systemStatus">{{ systemStatusText }}</view>
				</view>
				<view class="status-info">
					<text>版本: v1.0.0</text>
					<text>数据源: DFI Enterprise Data</text>
				</view>
			</view>

			<!-- 快速演示按钮组 -->
			<view class="section-title">一键演示</view>
			<view class="demo-grid">
				<view class="demo-card primary" @click="runFullDemo">
					<uni-icons type="play-filled" size="40" color="#fff"></uni-icons>
					<text class="demo-title">完整演示</text>
					<text class="demo-desc">自动展示所有功能</text>
				</view>
			</view>

			<!-- 功能模块按钮 -->
			<view class="section-title">功能模块</view>
			<view class="module-grid">
				<view class="module-card" @click="navTo('/pages/index/index')">
					<uni-icons type="home-filled" size="32" color="#0066CC"></uni-icons>
					<text class="module-title">首页看板</text>
					<text class="module-desc">KPI指标 · 趋势图</text>
				</view>
				<view class="module-card" @click="navTo('/pages/index/orders')">
					<uni-icons type="list" size="32" color="#FD7E14"></uni-icons>
					<text class="module-title">订单管理</text>
					<text class="module-desc">77,807 单真实数据</text>
				</view>
				<view class="module-card" @click="navTo('/pages/index/forcast')">
					<uni-icons type="eye-filled" size="32" color="#2E7D32"></uni-icons>
					<text class="module-title">需求预测</text>
					<text class="module-desc">Prophet模型</text>
				</view>
				<view class="module-card" @click="navTo('/pages/index/replenishment')">
					<uni-icons type="cart-filled" size="32" color="#9C27B0"></uni-icons>
					<text class="module-title">补货计划</text>
					<text class="module-desc">智能补货建议</text>
				</view>
				<view class="module-card" @click="navTo('/pages/index/deliever_map')">
					<uni-icons type="location-filled" size="32" color="#DC3545"></uni-icons>
					<text class="module-title">路径规划</text>
					<text class="module-desc">OR-Tools优化</text>
				</view>
				<view class="module-card" @click="showDriverModal">
					<uni-icons type="person-filled" size="32" color="#00BCD4"></uni-icons>
					<text class="module-title">派送员管理</text>
					<text class="module-desc">{{ driverCount }} 位司机</text>
				</view>
			</view>

			<!-- AI功能区 -->
			<view class="section-title">
				<text>AI智能助手</text>
				<view class="ai-badge">Powered by AWS Bedrock</view>
			</view>
			<view class="ai-section">
				<view class="ai-buttons">
					<button class="ai-btn" @click="analyzeTraffic">
						<uni-icons type="car-filled" size="20" color="#fff"></uni-icons>
						<text>路况分析</text>
					</button>
					<button class="ai-btn" @click="analyzeSLA">
						<uni-icons type="checkbox-filled" size="20" color="#fff"></uni-icons>
						<text>SLA诊断</text>
					</button>
					<button class="ai-btn" @click="analyzeRoute">
						<uni-icons type="navigate-filled" size="20" color="#fff"></uni-icons>
						<text>路径优化</text>
					</button>
					<button class="ai-btn" @click="analyzeDemand">
						<uni-icons type="bars" size="20" color="#fff"></uni-icons>
						<text>需求预测</text>
					</button>
				</view>
				
				<!-- AI对话区 -->
				<view class="ai-chat">
					<view class="chat-input-row">
						<input 
							class="chat-input" 
							v-model="chatMessage" 
							placeholder="向AI助手提问..."
							@confirm="sendChat"
						/>
						<button class="send-btn" @click="sendChat" :disabled="!chatMessage.trim()">
							<uni-icons type="paperplane-filled" size="20" color="#fff"></uni-icons>
						</button>
					</view>
					<view v-if="aiResponse" class="ai-response">
						<view class="response-header">
							<uni-icons type="chat-filled" size="16" color="#0066CC"></uni-icons>
							<text>AI助手回复</text>
						</view>
						<text class="response-text">{{ aiResponse }}</text>
					</view>
				</view>
			</view>

			<!-- 数据统计 -->
			<view class="section-title">数据概览</view>
			<view class="stats-grid">
				<view class="stat-item">
					<text class="stat-value">{{ summary.stores || 0 }}</text>
					<text class="stat-label">门店数</text>
				</view>
				<view class="stat-item">
					<text class="stat-value">{{ formatNumber(summary.orders) }}</text>
					<text class="stat-label">订单数</text>
				</view>
				<view class="stat-item">
					<text class="stat-value">{{ summary.slaRate || 0 }}%</text>
					<text class="stat-label">SLA达成率</text>
				</view>
				<view class="stat-item">
					<text class="stat-value">{{ summary.vehicles || 0 }}</text>
					<text class="stat-label">配送车辆</text>
				</view>
			</view>

			<!-- 系统亮点 -->
			<view class="section-title">系统亮点</view>
			<view class="highlights">
				<view class="highlight-item" v-for="(item, i) in highlights" :key="i">
					<uni-icons type="checkbox-filled" size="18" color="#2E7D32"></uni-icons>
					<text>{{ item }}</text>
				</view>
			</view>

			<view style="height: 40rpx;"></view>
		</scroll-view>

		<!-- 派送员管理弹窗 -->
		<view v-if="showDriverPanel" class="modal-overlay" @click.self="closeDriverModal">
			<view class="driver-modal" @click.stop>
				<view class="modal-header">
					<text class="modal-title">派送员管理</text>
					<view class="close-btn" @click="closeDriverModal">
						<uni-icons type="close" size="20" color="#666"></uni-icons>
					</view>
				</view>
				
				<view class="driver-actions">
					<button class="add-driver-btn" @click="showAddDriver = true">
						<uni-icons type="plusempty" size="16" color="#fff"></uni-icons>
						<text>添加派送员</text>
					</button>
				</view>
				
				<scroll-view scroll-y class="driver-list">
					<view 
						v-for="driver in drivers" 
						:key="driver.driver_id"
						class="driver-card"
					>
						<view class="driver-info">
							<text class="driver-name">{{ driver.name }}</text>
							<text class="driver-phone">{{ driver.phone }}</text>
						</view>
						<view class="driver-meta">
							<text class="driver-vehicle">{{ driver.vehicle_id || '未分配车辆' }}</text>
							<view class="driver-status" :class="driver.status">
								{{ statusText(driver.status) }}
							</view>
						</view>
					</view>
				</scroll-view>
				
				<!-- 添加派送员表单 -->
				<view v-if="showAddDriver" class="add-form">
					<view class="form-title">添加新派送员</view>
					<input class="form-input" v-model="newDriver.name" placeholder="姓名" />
					<input class="form-input" v-model="newDriver.phone" placeholder="电话" />
					<input class="form-input" v-model="newDriver.license_number" placeholder="驾照编号(可选)" />
					<view class="form-actions">
						<button class="btn-cancel" @click="showAddDriver = false">取消</button>
						<button class="btn-confirm" @click="createDriver">确认添加</button>
					</view>
				</view>
			</view>
		</view>

		<!-- AI分析结果弹窗 -->
		<uni-popup ref="aiPopup" type="center">
			<view class="ai-result-card">
				<view class="result-header">
					<uni-icons type="chat-filled" size="24" color="#0066CC"></uni-icons>
					<text class="result-title">{{ aiResultTitle }}</text>
				</view>
				<scroll-view scroll-y class="result-content">
					<text>{{ aiResultContent }}</text>
				</scroll-view>
				<button class="btn-close" @click="$refs.aiPopup.close()">关闭</button>
			</view>
		</uni-popup>

		<view class="tab-bar-placeholder"></view>
		<AppTabBar />
	</view>
</template>

<script>
import { apiGet, apiPost } from '../../utils/api.js'
import AppNavBar from '../../components/app-nav-bar.vue'
import AppTabBar from '../../components/app-tab-bar.vue'

export default {
	components: { AppNavBar, AppTabBar },
	data() {
		return {
			systemStatus: 'online',
			systemStatusText: '运行中',
			
			// 数据摘要
			summary: {
				stores: 0,
				orders: 0,
				slaRate: 0,
				vehicles: 0
			},
			
			highlights: [],
			
			// AI
			chatMessage: '',
			aiResponse: '',
			aiResultTitle: '',
			aiResultContent: '',
			
			// 派送员
			showDriverPanel: false,
			showAddDriver: false,
			drivers: [],
			driverCount: 0,
			newDriver: {
				name: '',
				phone: '',
				license_number: ''
			}
		}
	},
	onLoad() {
		this.loadSummary()
		this.loadDrivers()
	},
	methods: {
		goBack() {
			uni.navigateBack()
		},
		
		navTo(url) {
			uni.reLaunch({ url })
		},
		
		formatNumber(num) {
			if (!num) return '0'
			return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
		},
		
		async loadSummary() {
			try {
				const res = await apiGet('/ai/demo/summary')
				if (res && res.success && res.data) {
					const d = res.data
					this.summary = {
						stores: d.data_status?.stores || 0,
						orders: d.data_status?.total_orders || 0,
						slaRate: d.data_status?.sla_rate || 0,
						vehicles: d.logistics?.active_vehicles || 0
					}
					this.highlights = d.highlights || []
				}
			} catch (e) {
				console.error('Load summary error:', e)
			}
		},
		
		async loadDrivers() {
			try {
				const res = await apiGet('/drivers/list')
				if (res && res.success && res.data) {
					this.drivers = res.data.drivers || []
					this.driverCount = res.data.total || 0
				}
			} catch (e) {
				console.error('Load drivers error:', e)
			}
		},
		
		// 演示功能
		async runFullDemo() {
			uni.showModal({
				title: '完整演示',
				content: '将依次展示：首页看板 → 订单管理 → 需求预测 → 路径规划',
				confirmText: '开始演示',
				success: (res) => {
					if (res.confirm) {
						this.navTo('/pages/index/index')
					}
				}
			})
		},
		
		// AI功能
		async analyzeTraffic() {
			uni.showLoading({ title: 'AI分析中...' })
			try {
				const res = await apiPost('/ai/analyze/traffic')
				uni.hideLoading()
				if (res && res.success) {
					this.aiResultTitle = '路况分析结果'
					this.aiResultContent = res.data?.analysis || '分析完成'
					this.$refs.aiPopup.open()
				}
			} catch (e) {
				uni.hideLoading()
				uni.showToast({ title: '分析失败', icon: 'none' })
			}
		},
		
		async analyzeSLA() {
			uni.showLoading({ title: 'AI分析中...' })
			try {
				const res = await apiPost('/ai/analyze/sla')
				uni.hideLoading()
				if (res && res.success) {
					this.aiResultTitle = 'SLA风险分析'
					this.aiResultContent = res.data?.analysis || '分析完成'
					this.$refs.aiPopup.open()
				}
			} catch (e) {
				uni.hideLoading()
				uni.showToast({ title: '分析失败', icon: 'none' })
			}
		},
		
		async analyzeRoute() {
			uni.showLoading({ title: 'AI分析中...' })
			try {
				const res = await apiPost('/ai/analyze/route')
				uni.hideLoading()
				if (res && res.success) {
					this.aiResultTitle = '路径优化建议'
					this.aiResultContent = res.data?.analysis || '分析完成'
					this.$refs.aiPopup.open()
				}
			} catch (e) {
				uni.hideLoading()
				uni.showToast({ title: '分析失败', icon: 'none' })
			}
		},
		
		async analyzeDemand() {
			uni.showLoading({ title: 'AI分析中...' })
			try {
				const res = await apiPost('/ai/analyze/demand')
				uni.hideLoading()
				if (res && res.success) {
					this.aiResultTitle = '需求预测分析'
					this.aiResultContent = res.data?.analysis || '分析完成'
					this.$refs.aiPopup.open()
				}
			} catch (e) {
				uni.hideLoading()
				uni.showToast({ title: '分析失败', icon: 'none' })
			}
		},
		
		async sendChat() {
			if (!this.chatMessage.trim()) return
			
			uni.showLoading({ title: '思考中...' })
			try {
				const res = await apiPost('/ai/chat', {
					message: this.chatMessage
				})
				uni.hideLoading()
				if (res && res.success) {
					this.aiResponse = res.response || '抱歉，我暂时无法回答这个问题。'
				}
				this.chatMessage = ''
			} catch (e) {
				uni.hideLoading()
				this.aiResponse = 'AI服务暂时不可用，请稍后重试。'
			}
		},
		
		// 派送员管理
		showDriverModal() {
			this.showDriverPanel = true
			this.loadDrivers()
		},
		
		closeDriverModal() {
			this.showDriverPanel = false
			this.showAddDriver = false
		},
		
		statusText(status) {
			const map = {
				'available': '空闲',
				'on_duty': '执勤中',
				'off_duty': '休息'
			}
			return map[status] || status
		},
		
		async createDriver() {
			if (!this.newDriver.name || !this.newDriver.phone) {
				uni.showToast({ title: '请填写姓名和电话', icon: 'none' })
				return
			}
			
			try {
				const res = await apiPost('/drivers/create', this.newDriver)
				if (res && res.success) {
					uni.showToast({ title: '添加成功', icon: 'success' })
					this.showAddDriver = false
					this.newDriver = { name: '', phone: '', license_number: '' }
					this.loadDrivers()
				}
			} catch (e) {
				uni.showToast({ title: '添加失败', icon: 'none' })
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
	padding: 20rpx;
	box-sizing: border-box;
}

.tab-bar-placeholder {
	height: 120rpx;
}

/* 状态卡片 */
.status-card {
	background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	border-radius: 20rpx;
	padding: 30rpx;
	margin-bottom: 24rpx;
	color: #fff;
}

.status-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16rpx;
}

.status-title {
	font-size: 36rpx;
	font-weight: bold;
}

.status-badge {
	padding: 8rpx 20rpx;
	border-radius: 20rpx;
	font-size: 24rpx;
	
	&.online {
		background: #2E7D32;
	}
	
	&.offline {
		background: #DC3545;
	}
}

.status-info {
	display: flex;
	gap: 24rpx;
	font-size: 24rpx;
	opacity: 0.9;
}

/* 区块标题 */
.section-title {
	display: flex;
	align-items: center;
	gap: 12rpx;
	font-size: 30rpx;
	font-weight: bold;
	color: #333;
	margin: 24rpx 0 16rpx;
	padding-left: 16rpx;
	border-left: 6rpx solid #0066CC;
}

.ai-badge {
	font-size: 20rpx;
	color: #fff;
	background: linear-gradient(135deg, #FF6B35, #F7931E);
	padding: 4rpx 12rpx;
	border-radius: 8rpx;
	font-weight: normal;
}

/* 演示按钮 */
.demo-grid {
	display: flex;
	gap: 16rpx;
}

.demo-card {
	flex: 1;
	background: linear-gradient(135deg, #2E7D32 0%, #43a047 100%);
	border-radius: 20rpx;
	padding: 40rpx;
	text-align: center;
	color: #fff;
	
	&.primary {
		background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	}
}

.demo-title {
	display: block;
	font-size: 32rpx;
	font-weight: bold;
	margin-top: 16rpx;
}

.demo-desc {
	display: block;
	font-size: 24rpx;
	opacity: 0.9;
	margin-top: 8rpx;
}

/* 模块网格 */
.module-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 16rpx;
}

.module-card {
	width: calc(33.33% - 12rpx);
	background: #fff;
	border-radius: 16rpx;
	padding: 24rpx;
	text-align: center;
	box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
}

.module-title {
	display: block;
	font-size: 26rpx;
	font-weight: bold;
	color: #333;
	margin-top: 12rpx;
}

.module-desc {
	display: block;
	font-size: 20rpx;
	color: #999;
	margin-top: 6rpx;
}

/* AI区域 */
.ai-section {
	background: #fff;
	border-radius: 16rpx;
	padding: 24rpx;
}

.ai-buttons {
	display: flex;
	gap: 12rpx;
	margin-bottom: 20rpx;
}

.ai-btn {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 8rpx;
	background: linear-gradient(135deg, #0066CC 0%, #0088dd 100%);
	color: #fff;
	border-radius: 12rpx;
	padding: 16rpx 8rpx;
	font-size: 22rpx;
}

.ai-chat {
	border-top: 1rpx solid #eee;
	padding-top: 20rpx;
}

.chat-input-row {
	display: flex;
	gap: 12rpx;
}

.chat-input {
	flex: 1;
	background: #f5f5f5;
	border-radius: 12rpx;
	padding: 16rpx 20rpx;
	font-size: 28rpx;
}

.send-btn {
	width: 80rpx;
	height: 80rpx;
	background: #0066CC;
	border-radius: 12rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	
	&:disabled {
		opacity: 0.5;
	}
}

.ai-response {
	margin-top: 20rpx;
	background: #f0f7ff;
	border-radius: 12rpx;
	padding: 20rpx;
}

.response-header {
	display: flex;
	align-items: center;
	gap: 8rpx;
	margin-bottom: 12rpx;
	font-size: 24rpx;
	color: #0066CC;
	font-weight: bold;
}

.response-text {
	font-size: 26rpx;
	color: #333;
	line-height: 1.6;
}

/* 统计网格 */
.stats-grid {
	display: flex;
	gap: 16rpx;
}

.stat-item {
	flex: 1;
	background: #fff;
	border-radius: 16rpx;
	padding: 20rpx;
	text-align: center;
}

.stat-value {
	display: block;
	font-size: 36rpx;
	font-weight: bold;
	color: #0066CC;
}

.stat-label {
	display: block;
	font-size: 22rpx;
	color: #999;
	margin-top: 8rpx;
}

/* 亮点 */
.highlights {
	background: #fff;
	border-radius: 16rpx;
	padding: 20rpx;
}

.highlight-item {
	display: flex;
	align-items: center;
	gap: 12rpx;
	padding: 12rpx 0;
	font-size: 26rpx;
	color: #333;
	border-bottom: 1rpx solid #f0f0f0;
	
	&:last-child {
		border-bottom: none;
	}
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

.driver-modal {
	width: 85%;
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

.driver-actions {
	padding: 20rpx 24rpx;
}

.add-driver-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8rpx;
	background: #0066CC;
	color: #fff;
	border-radius: 12rpx;
	padding: 16rpx;
	font-size: 28rpx;
}

.driver-list {
	max-height: 40vh;
	padding: 0 24rpx;
}

.driver-card {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 20rpx 0;
	border-bottom: 1rpx solid #f0f0f0;
}

.driver-name {
	font-size: 28rpx;
	font-weight: bold;
	color: #333;
}

.driver-phone {
	font-size: 24rpx;
	color: #999;
	margin-top: 6rpx;
	display: block;
}

.driver-vehicle {
	font-size: 24rpx;
	color: #666;
}

.driver-status {
	font-size: 22rpx;
	padding: 4rpx 12rpx;
	border-radius: 8rpx;
	margin-top: 8rpx;
	
	&.available {
		background: #e8f5e9;
		color: #2E7D32;
	}
	
	&.on_duty {
		background: #fff3e0;
		color: #F57C00;
	}
	
	&.off_duty {
		background: #f5f5f5;
		color: #999;
	}
}

.add-form {
	padding: 24rpx;
	border-top: 1rpx solid #eee;
}

.form-title {
	font-size: 28rpx;
	font-weight: bold;
	margin-bottom: 16rpx;
}

.form-input {
	width: 100%;
	background: #f5f5f5;
	border-radius: 8rpx;
	padding: 16rpx;
	margin-bottom: 12rpx;
	font-size: 28rpx;
}

.form-actions {
	display: flex;
	gap: 16rpx;
	margin-top: 16rpx;
}

.btn-cancel {
	flex: 1;
	background: #f5f5f5;
	color: #666;
	border-radius: 8rpx;
	padding: 16rpx;
}

.btn-confirm {
	flex: 1;
	background: #0066CC;
	color: #fff;
	border-radius: 8rpx;
	padding: 16rpx;
}

/* AI结果弹窗 */
.ai-result-card {
	width: 85vw;
	max-height: 70vh;
	background: #fff;
	border-radius: 20rpx;
	padding: 30rpx;
}

.result-header {
	display: flex;
	align-items: center;
	gap: 12rpx;
	margin-bottom: 20rpx;
}

.result-title {
	font-size: 32rpx;
	font-weight: bold;
	color: #333;
}

.result-content {
	max-height: 50vh;
	background: #f8f9fa;
	border-radius: 12rpx;
	padding: 20rpx;
	font-size: 26rpx;
	line-height: 1.8;
	color: #333;
	white-space: pre-wrap;
}

.btn-close {
	margin-top: 20rpx;
	background: #0066CC;
	color: #fff;
	border-radius: 12rpx;
	padding: 20rpx;
}
</style>
