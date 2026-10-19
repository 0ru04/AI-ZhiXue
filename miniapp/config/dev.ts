import type { UserConfigExport } from "@tarojs/cli"

export default {
  logger: {
    quiet: false,
    stats: true
  },
  mini: {},
  h5: {
    devServer: {
      host: '127.0.0.1',
      port: 10086,
      open: true,
    },
  }
} satisfies UserConfigExport<'webpack5'>
