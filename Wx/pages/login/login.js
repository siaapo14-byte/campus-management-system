// 登录页面逻辑
Page({
  data: {
    studentId: '',
    password: '',
    isLoading: false,
    loadingText: '登录中...'
  },

  onLoad() {
    // 检查是否已登录
    this.checkLoginStatus();
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    
    if (token && userInfo) {
      // 已登录，跳转到首页
      wx.switchTab({
        url: '/pages/index/index'
      });
    }
  },

  // 学号输入
  onStudentIdInput(e) {
    this.setData({
      studentId: e.detail.value
    });
  },

  // 密码输入
  onPasswordInput(e) {
    this.setData({
      password: e.detail.value
    });
  },

  // 学号密码登录
  handlePasswordLogin() {
    const { studentId, password } = this.data;
    
    if (!studentId.trim()) {
      wx.showToast({
        title: '请输入学号',
        icon: 'none'
      });
      return;
    }
    
    if (!password.trim()) {
      wx.showToast({
        title: '请输入密码',
        icon: 'none'
      });
      return;
    }

    this.setData({
      isLoading: true,
      loadingText: '登录中...'
    });

    wx.request({
      url: 'http://localhost:5000/api/auth/login',
      method: 'POST',
      data: {
        username: studentId,
        password: password
      },
      success: (res) => {
        this.hideLoading();
        if (res.data.success) {
          this.loginSuccess(res.data);
        } else {
          wx.showToast({
            title: res.data.message || '登录失败',
            icon: 'none'
          });
        }
      },
      fail: () => {
        this.hideLoading();
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  // 登录成功处理
  loginSuccess(data) {
    // 保存登录信息 - 注意字段名从access_token改为token
    wx.setStorageSync('token', data.token);
    wx.setStorageSync('userInfo', data.user);
    
    wx.showToast({
      title: '登录成功',
      icon: 'success'
    });

    // 跳转到首页
    setTimeout(() => {
      wx.switchTab({
        url: '/pages/index/index'
      });
    }, 1500);
  },

  // 隐藏加载提示
  hideLoading() {
    this.setData({
      isLoading: false
    });
  }
}); 