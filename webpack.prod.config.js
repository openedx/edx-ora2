process.env.BABEL_ENV = 'production';
process.env.NODE_ENV = 'production';

const { createConfig } = require('@edx/frontend-build');

const webpack = require('webpack');
const config = createConfig('webpack-prod');
const path = require('path');
const Dotenv = require('dotenv-webpack');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

Object.assign(config, {
  entry: {
    "openassessment-lms": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms_index.js'),
    "openassessment-studio": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/studio_index.js'),
    "openassessment-editor-textarea": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms/editors/oa_editor_textarea.js'),
    "openassessment-editor-tinymce": path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js'),
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
    }),
    new webpack.ProvidePlugin({
      Backgrid: path.resolve(path.join(__dirname, 'openassessment/xblock/static/js/lib/backgrid/backgrid'))
    }),
  ],
});

config.resolve.modules = ['node_modules'].concat(
  path.resolve(__dirname, 'openassessment/xblock/static/js/src')
);

module.exports = [config];
