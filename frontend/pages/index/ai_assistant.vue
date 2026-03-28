<template>
	<view class="container">
		<AppNavBar title="AI 智能助手" :show-back="true" :show-menu="false" @back="goBack" />

		<view class="chat-container">
			<!-- 聊天消息区 -->
			<scroll-view 
				scroll-y 
				class="chat-messages" 
				:scroll-top="scrollTop"
				:scroll-with-animation="true"
			>
				<!-- 欢迎消息 -->
				<view class="welcome-card" v-if="messages.length === 0">
					<view class="welcome-icon">
						<uni-icons type="chat-filled" size="48" color="#0066CC"></uni-icons>
					</view>
					<text class="welcome-title">你好，我是万宁AI助手</text>
					<text class="welcome-desc">我可以帮你分析订单、SLA、库存、配送等业务数据</text>
					
					<view class="quick-questions">
						<text class="quick-label">快速提问</text>
						<view class="quick-list">
							<view 
								class="quick-item" 
								v-for="(q, i) in quickQuestions" 
								:key="i"
								@click="sendQuickQuestion(q)"
							>
								{{ q }}
							</view>
						</view>
					</view>
				</view>
				
				<!-- 消息列表 -->
				<view class="message-list">
					<view 
						v-for="(msg, index) in messages" 
						:key="index" 
						class="message-item"
						:class="msg.role"
					>
						<view class="message-avatar">
							<uni-icons 
								:type="msg.role === 'user' ? 'person-filled' : 'chat-filled'" 
								size="24" 
								:color="msg.role === 'user' ? '#fff' : '#fff'"
							></uni-icons>
						</view>
						<view class="message-content">
							<view class="message-bubble">
								<text class="message-text" :user-select="true">{{ msg.content }}</text>
							</view>
							<view class="message-meta" v-if="msg.retrievedData && msg.retrievedData.length">
								<uni-icons type="info" size="12" color="#999"></uni-icons>
								<text>数据来源: {{ msg.retrievedData.join(', ') }}</text>
							</view>
							<text class="message-time">{{ formatTime(msg.timestamp) }}</text>
						</view>
					</view>
					
					<!-- 加载中 -->
					<view v-if="loading" class="message-item assistant">
						<view class="message-avatar">
							<uni-icons type="chat-filled" size="24" color="#fff"></uni-icons>
						</view>
						<view class="message-content">
							<view class="message-bubble loading">
								<view class="typing-indicator">
									<view class="dot"></view>
									<view class="dot"></view>
									<view class="dot"></view>
								</view>
							</view>
						</view>
					</view>
				</view>
				
				<view class="scroll-bottom"></view>
			</scroll-view>

			<!-- 功能按钮 -->
			<view class="function-bar">
				<view class="func-btn" @click="showCapabilities">
					<uni-icons type="help" size="20" color="#0066CC"></uni-icons>
					<text>功能</text>
				</view>
				<view class="func-btn" @click="clearChat">
					<uni-icons type="trash" size="20" color="#999"></uni-icons>
					<text>清空</text>
				</view>
			</view>

			<!-- 输入区 -->
			<view class="input-area">
				<view class="input-wrap">
					<textarea
						v-model="inputText"
						class="input-field"
						placeholder="输入问题，例如：当前SLA达成率是多少？"
						:auto-height="true"
						:maxlength="500"
						@confirm="sendMessage"
					/>
				</view>
				<button 
					class="send-btn" 
					:disabled="!inputText.trim() || loading"
					@click="sendMessage"
				>
					<uni-icons type="paperplane-filled" size="24" color="#fff"></uni-icons>
				</button>
			</view>
		</view>

		<!-- 功能说明弹窗 -->
		<uni-popup ref="capPopup" type="center">
			<view class="cap-popup">
				<view class="cap-header">
					<text class="cap-title">AI 助手能力</text>
					<view class="close-btn" @click="$refs.capPopup.close()">
						<uni-icons type="close" size="20" color="#666"></uni-icons>
					</view>
				</view>
				<scroll-view scroll-y class="cap-content">
					<view class="cap-item" v-for="(cap, i) in capabilities" :key="i">
						<view class="cap-name">{{ cap.name }}</view>
						<view class="cap-desc">{{ cap.description }}</view>
						<view class="cap-examples">
							<text 
								class="example" 
								v-for="(ex, j) in cap.examples" 
								:key="j"
								@click="useExample(ex)"
							>{{ ex }}</text>
						</view>
					</view>
				</scroll-view>
			</view>
		</uni-popup>
	</view>
</template>

<script>
import { apiPost, apiGet } from '../../utils/api.js'
import AppNavBar from '../../components/app-nav-bar.vue'

export default {
	components: { AppNavBar },
	data() {
		return {
			inputText: '',
			messages: [],
			loading: false,
			scrollTop: 0,
			capabilities: [],
			quickQuestions: [
				'当前系统运行状态如何？',
				'今天的SLA达成率是多少？',
				'最近订单趋势怎么样？',
				'哪些门店需要补货？',
				'当前配送调度情况'
			]
		}
	},
	onLoad() {
		this.loadCapabilities()
	},
	methods: {
		goBack() {
			uni.navigateBack()
		},
		
		async loadCapabilities() {
			try {
				const res = await apiGet('/ai/rag/capabilities')
				if (res && res.success) {
					this.capabilities = res.capabilities || []
					if (res.quick_questions) {
						this.quickQuestions = res.quick_questions
					}
				}
			} catch (e) {
				console.error('Load capabilities error:', e)
			}
		},
		
		async sendMessage() {
			const text = this.inputText.trim()
			if (!text || this.loading) return
			
			// 添加用户消息
			this.messages.push({
				role: 'user',
				content: text,
				timestamp: new Date().toISOString()
			})
			
			this.inputText = ''
			this.loading = true
			this.scrollToBottom()
			
			try {
				// 构建历史记录
				const history = this.messages.slice(-10).map(m => ({
					role: m.role,
					content: m.content
				}))
				
				const res = await apiPost('/ai/rag/chat', {
					message: text,
					history: history
				})
				
				if (res && res.success) {
					this.messages.push({
						role: 'assistant',
						content: res.response,
						retrievedData: res.retrieved_data || [],
						timestamp: res.timestamp || new Date().toISOString()
					})
				} else {
					this.messages.push({
						role: 'assistant',
						content: res.response || '抱歉，我暂时无法回答这个问题。',
						timestamp: new Date().toISOString()
					})
				}
			} catch (e) {
				console.error('Send message error:', e)
				this.messages.push({
					role: 'assistant',
					content: '网络错误，请检查后端服务是否正常运行。',
					timestamp: new Date().toISOString()
				})
			} finally {
				this.loading = false
				this.scrollToBottom()
			}
		},
		
		sendQuickQuestion(question) {
			this.inputText = question
			this.sendMessage()
		},
		
		useExample(example) {
			this.$refs.capPopup.close()
			this.inputText = example
			this.sendMessage()
		},
		
		showCapabilities() {
			this.$refs.capPopup.open()
		},
		
		clearChat() {
			uni.showModal({
				title: '确认清空',
				content: '确定要清空所有对话记录吗？',
				success: (res) => {
					if (res.confirm) {
						this.messages = []
					}
				}
			})
		},
		
		scrollToBottom() {
			this.$nextTick(() => {
				this.scrollTop = this.scrollTop + 9999
			})
		},
		
		formatTime(timestamp) {
			if (!timestamp) return ''
			const date = new Date(timestamp)
			const hours = date.getHours().toString().padStart(2, '0')
			const minutes = date.getMinutes().toString().padStart(2, '0')
			return `${hours}:${minutes}`
		}
	}
}
</script>

<style lang="scss" scoped>
.container {
	height: 100vh;
	background: #f4f7f9;
	display: flex;
	flex-direction: column;
}

.chat-container {
	flex: 1;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.chat-messages {
	flex: 1;
	padding: 20rpx;
}

/* 欢迎卡片 */
.welcome-card {
	background: #fff;
	border-radius: 24rpx;
	padding: 48rpx 32rpx;
	text-align: center;
	margin-bottom: 24rpx;
	box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.06);
}

.welcome-icon {
	margin-bottom: 24rpx;
}

.welcome-title {
	display: block;
	font-size: 36rpx;
	font-weight: bold;
	color: #333;
	margin-bottom: 12rpx;
}

.welcome-desc {
	display: block;
	font-size: 26rpx;
	color: #666;
	margin-bottom: 32rpx;
}

.quick-questions {
	text-align: left;
}

.quick-label {
	display: block;
	font-size: 24rpx;
	color: #999;
	margin-bottom: 16rpx;
	padding-left: 8rpx;
}

.quick-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
}

.quick-item {
	background: #e8f4fd;
	color: #0066CC;
	padding: 16rpx 24rpx;
	border-radius: 32rpx;
	font-size: 26rpx;
	
	&:active {
		background: #d0e8f9;
	}
}

/* 消息列表 */
.message-list {
	display: flex;
	flex-direction: column;
	gap: 24rpx;
}

.message-item {
	display: flex;
	gap: 16rpx;
	
	&.user {
		flex-direction: row-reverse;
		
		.message-avatar {
			background: #0066CC;
		}
		
		.message-bubble {
			background: #0066CC;
			color: #fff;
			border-radius: 24rpx 6rpx 24rpx 24rpx;
		}
		
		.message-content {
			align-items: flex-end;
		}
	}
	
	&.assistant {
		.message-avatar {
			background: linear-gradient(135deg, #2E7D32, #43a047);
		}
		
		.message-bubble {
			background: #fff;
			color: #333;
			border-radius: 6rpx 24rpx 24rpx 24rpx;
			box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
		}
	}
}

.message-avatar {
	width: 64rpx;
	height: 64rpx;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.message-content {
	max-width: 75%;
	display: flex;
	flex-direction: column;
	gap: 8rpx;
}

.message-bubble {
	padding: 20rpx 28rpx;
	
	&.loading {
		padding: 24rpx 32rpx;
	}
}

.message-text {
	font-size: 28rpx;
	line-height: 1.6;
	white-space: pre-wrap;
	word-break: break-word;
}

.message-meta {
	display: flex;
	align-items: center;
	gap: 6rpx;
	font-size: 20rpx;
	color: #999;
	padding: 0 8rpx;
}

.message-time {
	font-size: 20rpx;
	color: #bbb;
	padding: 0 8rpx;
}

/* 打字动画 */
.typing-indicator {
	display: flex;
	gap: 8rpx;
}

.dot {
	width: 12rpx;
	height: 12rpx;
	background: #999;
	border-radius: 50%;
	animation: typing 1.4s infinite;
	
	&:nth-child(2) {
		animation-delay: 0.2s;
	}
	&:nth-child(3) {
		animation-delay: 0.4s;
	}
}

@keyframes typing {
	0%, 60%, 100% {
		transform: translateY(0);
		opacity: 0.4;
	}
	30% {
		transform: translateY(-8rpx);
		opacity: 1;
	}
}

.scroll-bottom {
	height: 20rpx;
}

/* 功能栏 */
.function-bar {
	display: flex;
	gap: 24rpx;
	padding: 16rpx 24rpx;
	background: #fff;
	border-top: 1rpx solid #eee;
}

.func-btn {
	display: flex;
	align-items: center;
	gap: 8rpx;
	padding: 12rpx 20rpx;
	background: #f5f5f5;
	border-radius: 32rpx;
	font-size: 24rpx;
	color: #666;
	
	&:active {
		background: #eee;
	}
}

/* 输入区 */
.input-area {
	display: flex;
	gap: 16rpx;
	padding: 16rpx 24rpx 32rpx;
	background: #fff;
	align-items: flex-end;
}

.input-wrap {
	flex: 1;
	background: #f5f5f5;
	border-radius: 24rpx;
	padding: 16rpx 24rpx;
}

.input-field {
	width: 100%;
	max-height: 200rpx;
	font-size: 28rpx;
	line-height: 1.5;
}

.send-btn {
	width: 88rpx;
	height: 88rpx;
	background: linear-gradient(135deg, #0066CC, #0088dd);
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	
	&:disabled {
		opacity: 0.5;
	}
}

/* 功能弹窗 */
.cap-popup {
	width: 85vw;
	max-height: 70vh;
	background: #fff;
	border-radius: 24rpx;
	overflow: hidden;
}

.cap-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 28rpx;
	border-bottom: 1rpx solid #eee;
}

.cap-title {
	font-size: 32rpx;
	font-weight: bold;
}

.cap-content {
	max-height: 50vh;
	padding: 20rpx;
}

.cap-item {
	background: #f8f9fa;
	border-radius: 16rpx;
	padding: 20rpx;
	margin-bottom: 16rpx;
}

.cap-name {
	font-size: 28rpx;
	font-weight: bold;
	color: #0066CC;
	margin-bottom: 8rpx;
}

.cap-desc {
	font-size: 24rpx;
	color: #666;
	margin-bottom: 12rpx;
}

.cap-examples {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
}

.example {
	background: #e8f4fd;
	color: #0066CC;
	padding: 8rpx 16rpx;
	border-radius: 16rpx;
	font-size: 22rpx;
}
</style>
