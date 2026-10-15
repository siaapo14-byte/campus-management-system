// 分析页面逻辑
import * as echarts from '../../ec-canvas/echarts';

Page({
  data: {
    grades: [],
    totalCourses: 0,
    averageScore: 0,
    bestSubject: '',
    scoreDistribution: [],
    trendAnalysis: [],
    suggestions: [],
    isLoading: false,
    radarCourses: [],
    radarColors: [], // 新增：存储雷达图顶点颜色
    aboveClassCount: 0,
    belowClassCount: 0,
    failCount: 0,
    totalCount: 0,
    passRate: 0,
    aboveCourses: '',
    belowCourses: '',
    gpa: '0.00',
    ecRadar: {
      onInit: initRadarChart
    }
  },

  onLoad() {
    this.loadAnalysisData();
  },

  onShow() {
    // 每次显示页面时刷新数据
    this.loadAnalysisData();
  },

  // 加载分析数据
  loadAnalysisData() {
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
      url: 'http://localhost:5000/api/student/analysis',
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        this.setData({ isLoading: false });
        if (res.data.success) {
          const analysis = res.data.analysis;
          // 自动兼容pie_data结构
          const pieData = analysis.pie_data || [];
          const total = pieData.reduce((sum, item) => sum + (item.value || item.count || 0), 0) || 1;
          const scoreDistribution = pieData.map((item, idx) => ({
            range: item.range || item.name || '',
            count: item.count || item.value || 0,
            percentage: item.percentage || item.percent || (total ? (((item.value || item.count || 0) / total * 100).toFixed(1)) : '0'),
            // 兼容图例配色
            color: ['#52c41a', '#1890ff', '#faad14', '#ff7a45', '#ff4d4f'][idx % 5]
          }));
          this.setData({
            totalCourses: analysis.statistics.total_courses,
            averageScore: analysis.statistics.average_score,
            bestSubject: analysis.statistics.best_subject,
            scoreDistribution: scoreDistribution,
            trendAnalysis: this.generateTrendAnalysis(analysis.statistics),
            suggestions: this.generateSuggestions(analysis.statistics),
            radarCourses: analysis.radar_data.courses || [],
            radarColors: ['#4f9da6', '#ff7a45', '#faad14', '#1890ff', '#52c41a', '#b620e0', '#ff4d4f'], // 新增：传递雷达图顶点颜色
            aboveClassCount: 0,
            belowClassCount: 0
          });
          
          // 绘制图表
          this.drawCharts(analysis);

          // 动态生成雷达图option并渲染
          if (analysis.radar_data && analysis.radar_data.courses && analysis.radar_data.scores) {
            const indicators = analysis.radar_data.courses.map(name => ({ name, max: 100 }));
            const values = analysis.radar_data.scores;
            const radarColors = ['#4f9da6', '#ff7a45', '#faad14', '#1890ff', '#52c41a', '#b620e0', '#ff4d4f'];
            const option = {
              title: {
                text: '各科成绩雷达图',
                left: 'center',
                textStyle: { color: '#4f9da6', fontSize: 18 }
              },
              tooltip: {},
              radar: {
                indicator: indicators,
                name: { show: false } // 隐藏雷达图上的科目名
              },
              series: [{
                name: '成绩',
                type: 'radar',
                data: [
                  {
                    value: values,
                    name: '我的成绩',
                    areaStyle: { color: 'rgba(79,157,166,0.3)' },
                    lineStyle: { color: '#4f9da6' },
                    symbol: 'circle',
                    symbolSize: 10,
                    itemStyle: {
                      color: function(params) {
                        return radarColors[params.dataIndex % radarColors.length];
                      }
                    },
                    label: { show: false } // 不显示顶点分数
                  }
                ]
              }],
              legend: {
                show: true,
                bottom: 0,
                orient: 'horizontal',
                data: analysis.radar_data.courses,
                textStyle: { color: '#4f9da6', fontSize: 14 }
              }
            };
            setTimeout(() => {
              this.selectComponent('#radar-echarts').setOption(option, true);
            }, 300);
          }

          // 统计高于和低于班级平均分的课程数量
          let aboveCount = 0, belowCount = 0;
          if (analysis.bar_data && analysis.bar_data.personal_scores && analysis.bar_data.class_averages) {
            for (let i = 0; i < analysis.bar_data.courses.length; i++) {
              const myScore = analysis.bar_data.personal_scores[i] || 0;
              const classAvg = analysis.bar_data.class_averages[i] || 0;
              if (myScore > classAvg) aboveCount++;
              else if (myScore < classAvg) belowCount++;
            }
          }
          this.setData({
            aboveClassCount: aboveCount,
            belowClassCount: belowCount
          });

          // 统计挂科数、及格率、超过/低于班级平均分的课程名称、学分绩
          let failCount = 0, passCount = 0, totalCount = 0;
          let aboveCourses = [], belowCourses = [];
          let gpaSum = 0;
          if (analysis.bar_data && analysis.bar_data.personal_scores && analysis.bar_data.class_averages) {
            for (let i = 0; i < analysis.bar_data.courses.length; i++) {
              const myScore = analysis.bar_data.personal_scores[i] || 0;
              const classAvg = analysis.bar_data.class_averages[i] || 0;
              const courseName = analysis.bar_data.courses[i];
              totalCount++;
              // 及格线60分
              if (myScore >= 60) passCount++; else failCount++;
              // 超过/低于班级平均分
              if (myScore > classAvg) aboveCourses.push(courseName);
              else if (myScore < classAvg) belowCourses.push(courseName);
              // GPA算法（4分制，简单线性）：GPA = (分数/100)*4
              gpaSum += (myScore / 100) * 4;
            }
          }
          const passRate = totalCount ? Math.round(passCount / totalCount * 100) : 0;
          const gpa = totalCount ? (gpaSum / totalCount).toFixed(2) : '0.00';
          this.setData({
            failCount,
            totalCount,
            passRate,
            aboveCourses: aboveCourses.join('、'),
            belowCourses: belowCourses.join('、'),
            gpa
          });
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

  // 生成趋势分析
  generateTrendAnalysis(statistics) {
    const trends = [];

    // 分析优秀表现
    if (statistics.average_score >= 85) {
      trends.push({
        type: 'excellent',
        icon: '🏆',
        label: '整体优秀',
        description: '你的平均分很高，学习状态很好！'
      });
    } else if (statistics.average_score >= 75) {
      trends.push({
        type: 'good',
        icon: '👍',
        label: '整体良好',
        description: '你的学习状态不错，还有提升空间'
      });
    } else {
      trends.push({
        type: 'danger',
        icon: '📚',
        label: '需要努力',
        description: '建议制定学习计划，提高整体成绩'
      });
    }

    // 分析课程数量
    if (statistics.total_courses < 5) {
      trends.push({
        type: 'warning',
        icon: '⚠️',
        label: '课程较少',
        description: '选课数量较少，建议多选一些课程'
      });
    }

    return trends;
  },

  // 生成学习建议
  generateSuggestions(statistics) {
    const suggestions = [];

    // 基于平均分的建议
    if (statistics.average_score < 70) {
      suggestions.push('制定详细的学习计划，合理安排时间');
      suggestions.push('多与老师沟通，及时解决学习中的问题');
      suggestions.push('参加学习小组，与同学互相帮助');
    } else if (statistics.average_score < 80) {
      suggestions.push('巩固基础知识，查漏补缺');
      suggestions.push('多做练习题，提高解题能力');
      suggestions.push('保持良好的学习习惯，坚持复习');
    } else {
      suggestions.push('继续保持优秀的学习状态');
      suggestions.push('可以尝试更有挑战性的学习内容');
      suggestions.push('帮助其他同学，共同进步');
    }

    // 基于课程数量的建议
    if (statistics.total_courses < 5) {
      suggestions.push('建议多选一些课程，丰富知识面');
    }

    return suggestions.slice(0, 5); // 最多显示5条建议
  },

  // 绘制图表
  drawCharts(analysis) {
    if (!analysis.radar_data.courses.length) return;

    // 绘制雷达图
    this.drawRadarChart(analysis.radar_data);
    
    // 绘制饼图
    this.drawPieChart(analysis.pie_data);
    
    // 绘制柱状图
    this.drawBarChart(analysis.bar_data);
  },

  // 绘制雷达图
  drawRadarChart(radarData) {
    const ctx = wx.createCanvasContext('radarChart');
    const canvasWidth = 260;
    const canvasHeight = 260;
    const centerX = canvasWidth / 2+30;
    const centerY = canvasHeight / 2-40;
    const radius = 60;
    const subjectColors = ['#4f9da6', '#ff7a45', '#faad14', '#1890ff', '#52c41a', '#b620e0', '#ff4d4f'];

    // 清空画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // 绘制网格
    ctx.strokeStyle = '#e8e8e8';
    ctx.lineWidth = 1;
    for (let i = 1; i <= 5; i++) {
      const r = (radius / 5) * i;
      ctx.beginPath();
      ctx.arc(centerX, centerY, r, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // 绘制轴线
    const subjects = radarData.courses;
    subjects.forEach((subject, index) => {
      const angle = (2 * Math.PI * index) / subjects.length;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.stroke();
    });

    // 绘制顶点科目名称
    subjects.forEach((subject, index) => {
      const angle = (2 * Math.PI * index) / subjects.length;
      const textRadius = radius + 18; // 文字离圆心距离
      const x = centerX + textRadius * Math.cos(angle);
      const y = centerY + textRadius * Math.sin(angle);
      ctx.font = '12px sans-serif';
      ctx.fillStyle = '#4f9da6';
      if (ctx.setTextAlign) ctx.setTextAlign('center');
      ctx.fillText(subject, x - 16, y + 6); // 可微调x/y
    });

    // 绘制数据点
    ctx.fillStyle = 'rgba(102, 126, 234, 0.3)';
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    
    ctx.beginPath();
    subjects.forEach((subject, index) => {
      const score = radarData.scores[index] || 0;
      const normalizedScore = score / 100;
      const angle = (2 * Math.PI * index) / subjects.length;
      const r = radius * normalizedScore;
      const x = centerX + r * Math.cos(angle);
      const y = centerY + r * Math.sin(angle);
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 绘制顶点彩色圆点（与雷达图顶点重合）
    subjects.forEach((subject, index) => {
      const angle = (2 * Math.PI * index) / subjects.length;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.setFillStyle ? ctx.setFillStyle(subjectColors[index % subjectColors.length]) : ctx.fillStyle = subjectColors[index % subjectColors.length];
      ctx.fill();
    });

    ctx.draw();
  },

  // 绘制饼图
  drawPieChart(pieData) {
    const ctx = wx.createCanvasContext('pieChart');
    const canvasWidth = 260;
    const canvasHeight = 260;
    const centerX = canvasWidth / 2+30;
    const centerY = canvasHeight / 2-35;
    const radius = 80;

    // 清空画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    const colors = ['#52c41a', '#1890ff', '#faad14', '#ff7a45', '#ff4d4f'];
    let startAngle = 0;
    const total = pieData.reduce((sum, item) => sum + item.value, 0);
    
    pieData.forEach((item, index) => {
      const percentage = item.value / total;
      const endAngle = startAngle + 2 * Math.PI * percentage;

      ctx.fillStyle = colors[index % colors.length];
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fill();

      startAngle = endAngle;
    });

    ctx.draw();
  },

  // 绘制柱状图
  drawBarChart(barData) {
    const ctx = wx.createCanvasContext('barChart');
    const canvasWidth = 260;
    const canvasHeight = 180; // 由220改为180，使柱状图整体变小
    const padding = 20;
    const chartWidth = canvasWidth - 2 * padding;
    const chartHeight = canvasHeight - 2 * padding;

    // 清空画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // 绘制坐标轴
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvasHeight - padding);
    ctx.lineTo(canvasWidth - padding, canvasHeight - padding);
    ctx.stroke();

    // 绘制双柱状图（你和班级平均分）
    const courses = barData.courses;
    const barGroupWidth = chartWidth / courses.length;
    const barWidth = barGroupWidth * 0.35;
    const barSpacing = barGroupWidth * 0.15;

    courses.forEach((course, index) => {
      // 你的分数
      const myScore = barData.personal_scores[index] || 0;
      const myBarHeight = (myScore / 100) * chartHeight;
      const myX = padding + index * barGroupWidth + barSpacing;
      const myY = canvasHeight - padding - myBarHeight;
      ctx.fillStyle = '#4f9da6'; // 主色
      ctx.fillRect(myX, myY, barWidth, myBarHeight);
      // 班级平均分
      const classScore = barData.class_averages[index] || 0;
      const classBarHeight = (classScore / 100) * chartHeight;
      const classX = myX + barWidth + barSpacing;
      const classY = canvasHeight - padding - classBarHeight;
      ctx.fillStyle = '#bfbfbf'; // 灰色
      ctx.fillRect(classX, classY, barWidth, classBarHeight);
      // 分数标签
      ctx.fillStyle = '#333';
      ctx.font = '12px sans-serif';
      ctx.fillText(myScore.toString(), myX + barWidth / 2 - 10, myY - 10);
      ctx.fillText(classScore.toString(), classX + barWidth / 2 - 10, classY - 10);
      // 课程名
      ctx.font = '10px sans-serif';
      ctx.fillText(course, myX, canvasHeight - padding + 15);
    });
    ctx.draw();
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadAnalysisData();
    wx.stopPullDownRefresh();
  }
});

function initRadarChart(canvas, width, height, dpr) {
  const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
  canvas.setChart(chart);
  return chart;
} 