// app.js
App({
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 登录
    wx.login({
      success: res => {
        // 发送 res.code 到后台换取 openId, sessionKey, unionId
      }
    })
  },
  globalData: {
    userInfo: null,
    // API 配置
    apiConfig: {
      baseUrl: 'http://localhost:8000', // 开发环境
      // baseUrl: 'https://your-domain.com', // 生产环境
      timeout: 30000
    }
  }
})