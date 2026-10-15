// 小程序配置文件
const config = {
  // 开发环境配置
  development: {
    baseUrl: '2409:895c:3387:f00:25de:1cb1:fc5:b409',
    debug: true
  },
  
  // 生产环境配置
  production: {
    baseUrl: 'https://your-domain.com/api', // 请替换为实际域名
    debug: false
  }
};

// 当前环境（开发时使用development，部署时改为production）
const currentEnv = 'development';

module.exports = {
  baseUrl: config[currentEnv].baseUrl,
  debug: config[currentEnv].debug,
  env: currentEnv
}; 