const path = require('path');

module.exports = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {
      if (process.env.NODE_ENV === 'production') {
        webpackConfig.optimization = {
          ...webpackConfig.optimization,
          splitChunks: {
            chunks: 'all',
            cacheGroups: {
              react: {
                test: /[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/,
                name: 'react-vendor',
                priority: 20,
                reuseExistingChunk: true,
              },
              recharts: {
                test: /[\\/]node_modules[\\/]recharts[\\/]/,
                name: 'recharts',
                priority: 15,
                reuseExistingChunk: true,
              },
              tanstack: {
                test: /[\\/]node_modules[\\/]@tanstack[\\/]/,
                name: 'tanstack',
                priority: 15,
                reuseExistingChunk: true,
              },
              radix: {
                test: /[\\/]node_modules[\\/]@radix-ui[\\/]/,
                name: 'radix',
                priority: 15,
                reuseExistingChunk: true,
              },
              vendor: {
                test: /[\\/]node_modules[\\/]/,
                name: 'vendors',
                priority: 10,
                reuseExistingChunk: true,
              },
              common: {
                minChunks: 2,
                priority: 5,
                reuseExistingChunk: true,
              },
            },
          },
        };
        webpackConfig.devtool = 'source-map';
      }

      return webpackConfig;
    },
  },
};
