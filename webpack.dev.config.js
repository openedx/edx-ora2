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

const fs = require('fs');

function getEntries(dir) {
  const entries = {};

  const traverseDirectory = (currentDir) => {
    const files = fs.readdirSync(currentDir);

    files.forEach(file => {
      const filePath = path.join(currentDir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        traverseDirectory(filePath);
      } else if (path.extname(filePath) === '.jsx') {
        let filePathEntry = filePath.replace('.jsx', '');
        if ( filePathEntry.endsWith('index') ) {
          filePathEntry = filePathEntry.replace('/index', '');
        }
        const relativePath = path.relative('openassessment/xblock/static/js/src/react/', filePathEntry);
        entries[relativePath] = path.resolve(process.cwd(), filePath);
      }
    });
  };

  traverseDirectory(dir);

  return entries;
}

// Get base config from edx-platform
let config = createConfig('webpack-dev');

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
    ...getEntries('openassessment/xblock/static/js/src/react/'),
  },
  output: {
    path: path.resolve(process.cwd(), 'openassessment/xblock/static/dist'),
    jsonpFunction: "o3iv79tz90732goag",
    chunkFilename: '[id].js',
    filename: '[name].js',
    publicPath: process.env.WEBPACK_DEV_SERVER ? `http://localhost:${config.devServer.port}/`: '',
  },
  optimization: {},
  plugins: [
    // Cleans the dist directory before each build
    new CleanWebpackPlugin(),
    new Dotenv({
      path: path.resolve(process.cwd(), '.env'),
      systemvars: true,
    }),
    new MiniCssExtractPlugin({
      filename: '[name].css',
    }),
    new webpack.ProvidePlugin({
      Backgrid: path.resolve(path.join(__dirname, 'openassessment/xblock/static/js/lib/backgrid/backgrid')),
    }),
    new WebpackManifestPlugin({
      writeToFileEmit: true,
      seed: {
        is_dev_server: process.env.WEBPACK_DEV_SERVER,
      },
    }),
    new webpack.HotModuleReplacementPlugin(),
  ],
});

config.resolve.modules = ['node_modules', path.resolve(__dirname, 'openassessment/xblock/static/js/src')];

module.exports = config;
