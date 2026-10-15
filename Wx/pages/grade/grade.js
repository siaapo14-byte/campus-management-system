// 成绩页面逻辑
Page({
  data: {
    grades: [],
    filteredGrades: [],
    totalCourses: 0,
    averageScore: 0,
    passRate: 0,
    searchKeyword: '',
    selectedScoreRange: 0,
    selectedCourseType: 0,
    scoreRanges: ['全部分数', '90分以上', '80-89分', '70-79分', '60-69分', '60分以下'],
    courseTypes: ['全部类型', '必修', '选修'],
    isLoading: false
  },

  onLoad() {
    this.loadGrades();
  },

  onShow() {
    // 每次显示页面时刷新数据
    this.loadGrades();
  },

  // 加载成绩数据
  loadGrades() {
    this.setData({ isLoading: true });

    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      wx.redirectTo({
        url: '/pages/login/login'
      });
      return;
    }

    wx.request({
      url: 'http://localhost:5000/api/student/grades',
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        this.setData({ isLoading: false });
        if (res.data.success) {
          const grades = res.data.grades || [];
          this.setData({ grades });
          this.calculateStats(grades);
          this.filterGrades();
        } else {
          wx.showToast({
            title: res.data.message || '加载失败',
            icon: 'none'
          });
        }
      },
      fail: () => {
        this.setData({ isLoading: false });
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 计算统计数据
  calculateStats(grades) {
    if (grades.length === 0) {
      this.setData({
        totalCourses: 0,
        averageScore: 0,
        passRate: 0
      });
      return;
    }

    const totalCourses = grades.length;
    const totalScore = grades.reduce((sum, grade) => sum + (grade.score || 0), 0);
    const averageScore = (totalScore / totalCourses).toFixed(1);
    const passCount = grades.filter(grade => (grade.score || 0) >= 60).length;
    const passRate = Math.round((passCount / totalCourses) * 100);

    this.setData({
      totalCourses,
      averageScore,
      passRate
    });
  },

  // 搜索输入
  onSearchInput(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
    this.filterGrades();
  },

  // 分数范围筛选
  onScoreRangeChange(e) {
    this.setData({
      selectedScoreRange: parseInt(e.detail.value)
    });
    this.filterGrades();
  },

  // 课程类型筛选
  onCourseTypeChange(e) {
    this.setData({
      selectedCourseType: parseInt(e.detail.value)
    });
    this.filterGrades();
  },

  // 筛选成绩
  filterGrades() {
    let filtered = [...this.data.grades];

    // 关键词搜索
    if (this.data.searchKeyword.trim()) {
      const keyword = this.data.searchKeyword.toLowerCase();
      filtered = filtered.filter(grade => 
        grade.course_name.toLowerCase().includes(keyword) ||
        grade.teacher_name.toLowerCase().includes(keyword)
      );
    }

    // 分数范围筛选
    if (this.data.selectedScoreRange > 0) {
      const score = this.data.selectedScoreRange;
      filtered = filtered.filter(grade => {
        const gradeScore = grade.score || 0;
        switch (score) {
          case 1: return gradeScore >= 90; // 90分以上
          case 2: return gradeScore >= 80 && gradeScore < 90; // 80-89分
          case 3: return gradeScore >= 70 && gradeScore < 80; // 70-79分
          case 4: return gradeScore >= 60 && gradeScore < 70; // 60-69分
          case 5: return gradeScore < 60; // 60分以下
          default: return true;
        }
      });
    }

    // 课程类型筛选
    if (this.data.selectedCourseType > 0) {
      const type = this.data.selectedCourseType;
      filtered = filtered.filter(grade => {
        const courseType = grade.course_type || '';
        switch (type) {
          case 1: return courseType === '必修';
          case 2: return courseType === '选修';
          default: return true;
        }
      });
    }

    this.setData({
      filteredGrades: filtered
    });
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadGrades();
    wx.stopPullDownRefresh();
  }
}); 