process.env.BABEL_ENV = 'development';
process.env.NODE_ENV = 'development';

const { createConfig } = require('@edx/frontend-build');

const config = createConfig('webpack-dev');
const path = require('path');
const Dotenv = require('dotenv-webpack');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

Object.assign(config, {
  entry: {
    "openassessment-lms": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms_index.js'),
    "openassessment-studio": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/studio_index.js'),
  },
  output: {
    path: path.resolve(process.cwd(), 'openassessment/xblock/static/js'),
  },
  optimization: {},
  plugins: [
    new Dotenv({
      path: path.resolve(process.cwd(), '.env'),
      systemvars: true,
    }),
    new MiniCssExtractPlugin({
      filename: '[name].css',
    })
  ],
});

config.resolve.modules = ['node_modules'].concat(
  // UPDATE ME
  path.resolve(__dirname, 'openassessment/xblock/static/js/src')
);

module.exports = config;
