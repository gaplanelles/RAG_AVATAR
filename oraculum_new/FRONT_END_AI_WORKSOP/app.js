const express = require("express");
var cors = require('cors')
const app = express();
app.use(cors());
const { createProxyMiddleware } = require('http-proxy-middleware');

app.use('/api', createProxyMiddleware({ 
    target: 'https://api.heygen.com/v1', //original url
    changeOrigin: true, 
    secure: true,
    ws: true,
    headers: {
        "Connection": "keep-alive"
    },
    onProxyRes: function (proxyRes, req, res) {
       proxyRes.headers['Access-Control-Allow-Origin'] = '*';
    },
    pathRewrite: {
        '^/api': '' // usuwa '/api' z URL przy przekierowaniu
    },
    logLevel: 'debug' // pomoże w debugowaniu

}));
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));
app.listen(3004, '0.0.0.0', () => {
    console.log('Proxy server is running on port 3004');
});