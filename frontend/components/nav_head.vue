<!-- 自定义搜索导航栏 -->
<template>
  <view class="search-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
    <view class="nav-content">
      <view class="nav-left" @click="goBack" v-if="showBack">
        <uni-icons type="arrowleft" size="24"></uni-icons>
      </view>
      
      <view class="search-box">
        <uni-icons type="search" size="18" color="#999"></uni-icons>
        <input 
          type="text" 
          placeholder="请输入关键词" 
          v-model="keyword"
          @confirm="onSearch"
        />
      </view>
      
      <view class="nav-right" @click="onCancel">
        取消
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      statusBarHeight: 0,
      keyword: ''
    }
  },
  mounted() {
    const systemInfo = uni.getSystemInfoSync()
    this.statusBarHeight = systemInfo.statusBarHeight
  },
  methods: {
    onSearch() {
      uni.navigateTo({
        url: `/pages/search/result?keyword=${this.keyword}`
      })
    },
    onCancel() {
      uni.navigateBack()
    }
  }
}
</script>

<style scoped>
.search-navbar {
  background: #fff;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.1);
}

.nav-content {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 20rpx;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 0 20rpx;
  margin: 0 20rpx;
  height: 32px;
}

.search-box input {
  flex: 1;
  height: 100%;
  margin-left: 10rpx;
  font-size: 14px;
}
</style>