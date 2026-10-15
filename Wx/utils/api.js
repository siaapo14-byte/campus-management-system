// API工具类
const config = require('../config.js');

class ApiService {
  // 获取请求头
  static getHeaders() {
    const token = wx.getStorageSync('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  }

  // 通用请求方法
  static request(url, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${config.baseUrl}${url}`,
        method: method,
        data: data,
        header: this.getHeaders(),
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else if (res.statusCode === 401) {
            // 未授权，跳转到登录页
            wx.removeStorageSync('token');
            wx.removeStorageSync('userInfo');
            wx.redirectTo({
              url: '/pages/login/login'
            });
            reject(new Error('未授权，请重新登录'));
          } else {
            reject(new Error(res.data.message || '请求失败'));
          }
        },
        fail: (err) => {
          if (config.debug) {
            console.error('API请求失败:', err);
          }
          reject(new Error('网络错误'));
        }
      });
    });
  }

  // 登录相关API
  static login(username, password) {
    return this.request('/auth/login', 'POST', { username, password });
  }

  static wechatLogin(code) {
    return this.request('/auth/wechat_login', 'POST', { code });
  }

  // 学生相关API
  static getStudentInfo() {
    return this.request('/student/info');
  }

  static getGrades() {
    return this.request('/student/grades');
  }

  static getCourses() {
    return this.request('/student/courses');
  }

  static getAnalysis() {
    return this.request('/student/analysis');
  }

  // 课程相关API
  static selectCourse(courseId) {
    return this.request('/student/select_course', 'POST', { course_id: courseId });
  }

  static dropCourse(courseId) {
    return this.request('/student/drop_course', 'POST', { course_id: courseId });
  }
}

module.exports = ApiService; 