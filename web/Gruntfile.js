var path = require('path');

var JS_DIR = path.resolve(__dirname, 'attpcdaq/static/js');
var BUILD_DIR = path.resolve(__dirname, 'attpcdaq/static/js/build');

module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        less: {
            site: {
                options: {
                    paths: [
                        'node_modules/bootstrap/dist/css',
                        'node_modules/font-awesome/css'
                    ]
                },
                files: {
                    'attpcdaq/static/css/site.css': 'attpcdaq/static/less/site.less'
                }
            }
        },

        copy: {
            fonts: {
                files: [{
                    expand: true,
                    src: ['node_modules/bootstrap/dist/fonts/*', 'node_modules/font-awesome/fonts/*'],
                    dest: 'attpcdaq/static/fonts/',
                    flatten: true,
                }]
            },
            bootstrapjs: {
                files: [{
                    expand: true,
                    src: ['node_modules/bootstrap/dist/js/bootstrap.min.js', 'node_modules/jquery/dist/jquery.min.js'],
                    dest: 'attpcdaq/static/js/build/',
                    flatten: true,
                }]
            }
        },

        webpack: {
            app: {
                entry: JS_DIR + '/app.jsx',
                output: {
                    path: BUILD_DIR,
                    filename: 'app.js'
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
            }
        },

        uglify: {
            statuspage: {
                files: {
                    'attpcdaq/static/js/build/status_page.min.js': ['attpcdaq/static/js/build/status_page.js']
                }
            }
        }
    });

    grunt.loadNpmTasks('grunt-contrib-less');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-webpack');
    grunt.loadNpmTasks('grunt-contrib-uglify');

    grunt.registerTask('default', ['less', 'copy', 'webpack', 'uglify']);
};