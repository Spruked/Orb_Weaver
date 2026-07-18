process.env.BABEL_ENV = 'production';
process.env.NODE_ENV = 'production';

const path = require('path');
const webpack = require('webpack');

const root = path.resolve(__dirname, '..');
const compiler = webpack({
  mode: 'production',
  target: ['web', 'es2018'],
  devtool: false,
  entry: path.join(root, 'src/adapters/external-script.ts'),
  output: {
    path: path.join(root, 'public'),
    filename: 'orb-loader.js',
    iife: true,
    clean: false,
  },
  resolve: { extensions: ['.ts', '.tsx', '.js'] },
  module: {
    rules: [{
      test: /\.[jt]sx?$/,
      exclude: /node_modules/,
      use: {
        loader: require.resolve('babel-loader'),
        options: {
          presets: [require.resolve('babel-preset-react-app')],
          cacheDirectory: true,
          cacheCompression: false,
        },
      },
    }],
  },
  optimization: { minimize: true },
});

compiler.run((error, stats) => {
  compiler.close(() => undefined);
  if (error) {
    console.error(error);
    process.exitCode = 1;
    return;
  }
  const output = stats.toString({ colors: true, chunks: false, modules: false });
  if (output) console.log(output);
  if (stats.hasErrors()) process.exitCode = 1;
});
