const { createConfig } = require('@edx/frontend-build');
const { mergeWithRules } = require('webpack-merge');

const webpack = require('webpack');
const path = require('path');
const Dotenv = require('dotenv-webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const PostCssAutoprefixerPlugin = require('autoprefixer');
const CssNano = require('cssnano');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

// Get base config from edx-platform
let config = createConfig('webpack-prod');

// Modify CSS processing rules (remove PostCssRtlPlugin)
const modifiedCssRule = {
  module: {
    rules: [
      {
        test: /(.scss|.css)$/,
        use: [
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader', // translates CSS into CommonJS
            options: {
              sourceMap: true,
            },
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: () => [
                  PostCssAutoprefixerPlugin({ grid: true }),
                  CssNano(),
                ],
              },
            },
          },
          'resolve-url-loader',
          {
            loader: 'sass-loader', // compiles Sass to CSS
            options: {
              sourceMap: true,
              sassOptions: {
                includePaths: [
                  path.join(process.cwd(), 'node_modules'),
                  path.join(process.cwd(), 'src'),
                ],
              },
            },
          },
        ],
      },
    ],
  },
};

// Merge back to configuration
config = mergeWithRules({
  module: {
    rules: {
      test: 'match',
      use: 'replace',
    },
  },
})(config, modifiedCssRule);

Object.assign(config, {
  entry: {
    'openassessment-lms': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms_index.js'),
    'openassessment-studio': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/studio_index.js'),
    'openassessment-rtl': path.resolve(process.cwd(), 'openassessment/xblock/static/sass/openassessment-rtl.scss'),
    'openassessment-ltr': path.resolve(process.cwd(), 'openassessment/xblock/static/sass/openassessment-ltr.scss'),
    'openassessment-editor-textarea': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms/editors/oa_editor_textarea.js'),
    'openassessment-editor-tinymce': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js'),
    'InitializeReact': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/react/InitializeReact.js'),
  },
  optimization: {},
  plugins: [
    // Cleans the dist directory before each build
    ...process.env.npm_config_clean ? [new CleanWebpackPlugin()]: [],
    new Dotenv({
      path: path.resolve(process.cwd(), '.env'),
      systemvars: true,
    }),
    new MiniCssExtractPlugin({
      filename: '[name].[chunkhash].css',
    }),
    new webpack.ProvidePlugin({
      Backgrid: path.resolve(path.join(__dirname, 'openassessment/xblock/static/js/lib/backgrid/backgrid')),
    }),
    new WebpackManifestPlugin({}),
  ],
});

config.resolve.modules = ['node_modules', path.resolve(__dirname, 'openassessment/xblock/static/js/src')];
config.output.path = path.resolve(process.cwd(), 'openassessment/xblock/static/dist');

module.exports = config;
