// pages/index/index.js
const app = getApp()

Page({
  data: {
    stockCode: '',
    authCode: '',
    loading: false,
    result: null,
    error: null,
    showResult: false,
    fileUrl: null
  },

  onLoad() {
    // 页面加载时的逻辑
    console.log('页面加载完成')
  },

  onPullDownRefresh() {
    // 下拉刷新
    wx.stopPullDownRefresh()
  },

  // 输入股票代码
  onStockCodeInput(e) {
    this.setData({
      stockCode: e.detail.value
    })
  },

  // 输入授权码
  onAuthCodeInput(e) {
    this.setData({
      authCode: e.detail.value
    })
  },

  // 分析股票
  async analyzeStock() {
    const { stockCode, authCode } = this.data

    // 验证输入
    if (!stockCode || stockCode.trim() === '') {
      wx.showToast({
        title: '请输入股票代码',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 验证股票代码格式
    const stockCodePattern = /^[0-9]{6}$/
    if (!stockCodePattern.test(stockCode)) {
      wx.showToast({
        title: '股票代码格式错误',
        icon: 'none',
        duration: 2000
      })
      return
    }

    this.setData({
      loading: true,
      error: null,
      result: null,
      showResult: false
    })

    try {
      // 调用后端 API
      const response = await this.callAnalyzeAPI(stockCode, authCode)

      if (response.success) {
        this.setData({
          result: response,
          showResult: true,
          loading: false
        })

        wx.showToast({
          title: '分析成功',
          icon: 'success',
          duration: 2000
        })
      } else {
        this.setData({
          error: response.message,
          loading: false
        })

        wx.showToast({
          title: response.message || '分析失败',
          icon: 'none',
          duration: 2000
        })
      }
    } catch (error) {
      console.error('分析失败:', error)
      this.setData({
        error: '网络错误，请稍后重试',
        loading: false
      })

      wx.showToast({
        title: '网络错误',
        icon: 'none',
        duration: 2000
      })
    }
  },

  // 调用分析 API
  callAnalyzeAPI(stockCode, authCode) {
    return new Promise((resolve, reject) => {
      const { apiConfig } = app.globalData
      const url = `${apiConfig.baseUrl}/analyze`

      wx.request({
        url: url,
        method: 'POST',
        data: {
          stock_code: stockCode,
          auth_code: authCode || undefined
        },
        header: {
          'content-type': 'application/json'
        },
        timeout: apiConfig.timeout,
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error(`请求失败: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },

  // 下载 Excel 文件
  async downloadExcel() {
    const { result } = this.data

    if (!result || !result.file_id) {
      wx.showToast({
        title: '文件不存在',
        icon: 'none',
        duration: 2000
      })
      return
    }

    wx.showLoading({
      title: '下载中...'
    })

    try {
      const { apiConfig } = app.globalData
      const url = `${apiConfig.baseUrl}/download/${result.file_id}`

      // 下载文件
      const downloadRes = await this.downloadFile(url)

      if (downloadRes.statusCode === 200) {
        const filePath = downloadRes.tempFilePath

        // 打开文件
        wx.openDocument({
          filePath: filePath,
          fileType: 'xlsx',
          success: () => {
            wx.hideLoading()
            wx.showToast({
              title: '打开成功',
              icon: 'success',
              duration: 2000
            })
          },
          fail: (err) => {
            wx.hideLoading()
            console.error('打开文件失败:', err)
            wx.showToast({
              title: '打开文件失败',
              icon: 'none',
              duration: 2000
            })
          }
        })
      } else {
        wx.hideLoading()
        wx.showToast({
          title: '下载失败',
          icon: 'none',
          duration: 2000
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('下载失败:', error)
      wx.showToast({
        title: '下载失败',
        icon: 'none',
        duration: 2000
      })
    }
  },

  // 下载文件
  downloadFile(url) {
    return new Promise((resolve, reject) => {
      const { apiConfig } = app.globalData

      wx.downloadFile({
        url: url,
        timeout: apiConfig.timeout * 2, // 下载超时时间加倍
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res)
          } else {
            reject(new Error(`下载失败: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },

  // 重新分析
  resetForm() {
    this.setData({
      stockCode: '',
      authCode: '',
      loading: false,
      result: null,
      error: null,
      showResult: false,
      fileUrl: null
    })
  },

  // 查看帮助
  showHelp() {
    wx.showModal({
      title: '使用说明',
      content: '1. 输入6位股票代码\n2. 可选输入授权码\n3. 点击"开始分析"\n4. 分析完成后下载Excel报告',
      showCancel: false,
      confirmText: '知道了'
    })
  }
})