
module.exports = {
    devServer: {
        proxy: {
            'api/' : {
                target: 'http://localhost:4231',
                ws: true, //代理websockets
                changeOrigin: true,
            },
            'admin/' : {
                target: 'http://localhost:4231',
                ws: true, //代理websockets
                changeOrigin: true,
            },
        }
    }
}