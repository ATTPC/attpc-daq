var webpack = require('webpack');
var path = require('path');

var JS_DIR = path.resolve(__dirname, 'attpcdaq/static/js');
var BUILD_DIR = path.resolve(__dirname, 'attpcdaq/static/js/build');

var config = {
    entry: JS_DIR + '/status_page.jsx',
    output: {
        path: BUILD_DIR,
        filename: 'status_page.js'
    },
    module: {
        loaders: [
            {
                test: /\.jsx?/,
                include: JS_DIR,
                loader: 'babel',
            }
        ]
    }
};

module.exports = config;