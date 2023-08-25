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
        const relativePath = path.join('pages', path.relative(dir, filePathEntry));
        entries[relativePath] = path.resolve(process.cwd(), filePath);
      }
    });
  };

  traverseDirectory(dir);

  return entries;
}

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
            // options: {
            //   sourceMap: true,
            // },
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
              // sourceMap: true,
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
    'react_base': path.resolve(process.cwd(), 'openassessment/xblock/static/js/src/react/react_base.jsx'),
    ...getEntries('openassessment/xblock/static/js/src/react/pages'),
  },
  // remove source map from production build
  devtool: false,
  output: {
    path: path.resolve(process.cwd(), 'openassessment/xblock/static/dist'),
    chunkFilename: '[id].js',
    filename: '[name].[hash].js',
    // this is require for the known bug with webpack 4 and lazy loading
    // https://github.com/webpack/webpack/issues/9766
    jsonpFunction: "o3iv79tz90732goag",
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
      filename: '[name].[hash].css',
    }),
    new webpack.ProvidePlugin({
      Backgrid: path.resolve(path.join(__dirname, 'openassessment/xblock/static/js/lib/backgrid/backgrid')),
    }),
    new WebpackManifestPlugin(),
  ],
  // externals: {
  //   'react': 'React',
  //   'react-dom': 'ReactDOM',
  // }
});

config.resolve.modules = ['node_modules', path.resolve(__dirname, 'openassessment/xblock/static/js/src')];

module.exports = config;
