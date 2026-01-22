const prodConfig = require('./webpack.prod.config.js');

// Use production webpack config but force development mode for tests
// This ensures React is built with test utilities like act() available
module.exports = {
  ...prodConfig,
  mode: 'development',
  // Remove optimization for faster test builds
  optimization: {
    minimize: false,
  },
  // Disable performance hints in tests
  performance: false,
};
