// index.js
const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'
const ApiService = require('../../utils/api.js');

Page({
  data: {
    motto: 'Hello World',
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    hasUserInfo: false,
    canIUseGetUserProfile: wx.canIUse('getUserProfile'),
    canIUseNicknameComp: wx.canIUse('input.type.nickname'),
    stats: {
      totalCourses: 0,
      averageScore: 0,
      passRate: 0
    },
    recentGrades: [],
    studyTips: [],
    isLoading: false
  },
  bindViewTap() {
    wx.navigateTo({
      url: '../logs/logs'
    })
  },
  onChooseAvatar(e) {
    const { avatarUrl } = e.detail
    const { nickName } = this.data.userInfo
    this.setData({
      "userInfo.avatarUrl": avatarUrl,
      hasUserInfo: nickName && avatarUrl && avatarUrl !== defaultAvatarUrl,
    })
  },
  onInputChange(e) {
    const nickName = e.detail.value
    const { avatarUrl } = this.data.userInfo
    this.setData({
      "userInfo.nickName": nickName,
      hasUserInfo: nickName && avatarUrl && avatarUrl !== defaultAvatarUrl,
    })
  },
  getUserProfile(e) {
    // 推荐使用wx.getUserProfile获取用户信息，开发者每次通过该接口获取用户个人信息均需用户确认，开发者妥善保管用户快速填写的头像昵称，避免重复弹窗
    wx.getUserProfile({
      desc: '展示用户信息', // 声明获取用户个人信息后的用途，后续会展示在弹窗中，请谨慎填写
      success: (res) => {
        console.log(res)
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        })
      }
    })
  },
  onLoad() {
    this.checkLoginStatus();
  },
  onShow() {
    // 每次显示页面时刷新数据
    if (this.data.userInfo.name) {
      this.loadPageData();
    }
  },
  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    
    if (token && userInfo) {
      this.setData({ userInfo });
      this.loadPageData();
    } else {
      // 未登录，跳转到登录页
      wx.redirectTo({
        url: '/pages/login/login'
      });
    }
  },
  // 加载页面数据
  loadPageData() {
    this.setData({ isLoading: true });

    // 并行加载多个数据
    Promise.all([
      this.loadStudentInfo(),
      this.loadGrades(),
      this.loadStudyTips()
    ]).then(() => {
      this.setData({ isLoading: false });
    }).catch((error) => {
      this.setData({ isLoading: false });
      wx.showToast({
        title: '数据加载失败',
        icon: 'none'
      });
    });
  },
  // 加载学生信息
  loadStudentInfo() {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      wx.request({
        url: 'http://localhost:5000/api/student/info',
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          if (res.data.success) {
            this.setData({ userInfo: res.data.student });
            // 更新本地存储
            wx.setStorageSync('userInfo', res.data.student);
            resolve();
          } else {
            reject(new Error(res.data.message));
          }
        },
        fail: reject
      });
    });
  },
  // 加载成绩数据
  loadGrades() {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      wx.request({
        url: 'http://localhost:5000/api/student/grades',
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          if (res.data.success) {
            const grades = res.data.grades || [];
            
            // 计算统计数据
            this.calculateStats(grades);
            
            // 获取最近3门成绩
            const recentGrades = grades.slice(0, 3);
            this.setData({ recentGrades });
            resolve();
          } else {
            reject(new Error(res.data.message));
          }
        },
        fail: reject
      });
    });
  },
  // 计算统计数据
  calculateStats(grades) {
    if (grades.length === 0) {
      this.setData({
        stats: {
          totalCourses: 0,
          averageScore: 0,
          passRate: 0
        }
      });
      return;
    }

    const totalCourses = grades.length;
    const totalScore = grades.reduce((sum, grade) => sum + (grade.score || 0), 0);
    const averageScore = (totalScore / totalCourses).toFixed(1);
    const passCount = grades.filter(grade => (grade.score || 0) >= 60).length;
    const passRate = Math.round((passCount / totalCourses) * 100);

    this.setData({
      stats: {
        totalCourses,
        averageScore,
        passRate
      }
    });
  },
  // 加载学习提醒
  loadStudyTips() {
    // 这里可以根据成绩数据生成学习提醒
    const tips = [];
    const { stats } = this.data;

    if (stats.averageScore < 70) {
      tips.push('你的平均分偏低，建议制定学习计划');
    }
    if (stats.passRate < 80) {
      tips.push('及格率有待提高，需要加强薄弱科目');
    }
    if (stats.totalCourses < 5) {
      tips.push('选课数量较少，建议多选一些课程');
    }

    if (tips.length === 0) {
      tips.push('学习状态良好，继续保持！');
    }

    this.setData({ studyTips: tips });
  },
  // 退出登录
  handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          wx.redirectTo({
            url: '/pages/login/login'
          });
        }
      }
    });
  },
  // 导航到成绩页面
  navigateToGrade() {
    wx.switchTab({
      url: '/pages/grade/grade'
    });
  },
  // 导航到课程页面
  navigateToCourse() {
    wx.switchTab({
      url: '/pages/course/course'
    });
  },
  // 导航到分析页面
  navigateToAnalysis() {
    wx.switchTab({
      url: '/pages/analysis/analysis'
    });
  },
  // 显示课程表
  showSchedule() {
    wx.showToast({
      title: '课程表功能开发中',
      icon: 'none'
    });
  },
  // 下拉刷新
  onPullDownRefresh() {
    this.loadPageData();
    wx.stopPullDownRefresh();
  }
})
