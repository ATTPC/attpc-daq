"use strict";

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var Modal = function (_React$Component) {
    _inherits(Modal, _React$Component);

    function Modal() {
        _classCallCheck(this, Modal);

        return _possibleConstructorReturn(this, (Modal.__proto__ || Object.getPrototypeOf(Modal)).apply(this, arguments));
    }

    _createClass(Modal, [{
        key: 'componentDidMount',
        value: function componentDidMount() {
            var $node = $(ReactDOM.findDOMNode(this));
            $node.modal('show');
            $node.on('hidden.bs.modal', this.props.handleHideModal);
        }
    }, {
        key: 'render',
        value: function render() {
            return React.createElement(
                'div',
                { className: 'modal fade' },
                React.createElement(
                    'div',
                    { className: 'modal-dialog modal-lg' },
                    React.createElement(
                        'div',
                        { className: 'modal-content' },
                        React.createElement(
                            'div',
                            { className: 'modal-header' },
                            React.createElement(
                                'button',
                                { type: 'button', className: 'close', 'data-dismiss': 'modal', 'aria-label': 'Close' },
                                React.createElement(
                                    'span',
                                    { 'aria-hidden': 'true' },
                                    '\xD7'
                                )
                            ),
                            React.createElement(
                                'h4',
                                { className: 'modal-title' },
                                this.props.title
                            )
                        ),
                        React.createElement(
                            'div',
                            { className: 'modal-body' },
                            React.createElement(
                                'pre',
                                null,
                                this.props.content
                            )
                        ),
                        React.createElement(
                            'div',
                            { className: 'modal-footer' },
                            React.createElement(
                                'button',
                                { type: 'button', className: 'btn btn-default', 'data-dismiss': 'modal' },
                                'Close'
                            )
                        )
                    )
                )
            );
        }
    }]);

    return Modal;
}(React.Component);

function get_label_class(state_name) {
    if (state_name == 'Idle') {
        return 'label-idle';
    } else if (state_name == 'Described') {
        return 'label-described';
    } else if (state_name == 'Prepared') {
        return 'label-prepared';
    } else if (state_name == 'Ready') {
        return 'label-ready';
    } else if (state_name == 'Running') {
        return 'label-running';
    } else {
        return 'label-error';
    }
}

function ECCStatusLabel(props) {
    var state_name = props.state_name;
    var is_transitioning = props.is_transitioning;

    if (is_transitioning) {
        return React.createElement('span', { className: 'fa fa-pulse fa-spinner' });
    } else {
        var label_class = get_label_class(state_name);
        return React.createElement(
            'span',
            { className: 'label ' + label_class },
            state_name
        );
    }
}

function get_config_text(config) {
    if (config) {
        return config.describe + '/' + config.prepare + '/' + config.configure;
    } else {
        return '';
    }
}

function EccControlButton(props) {
    var icon_class = void 0;
    switch (props.action) {
        case 'describe':
            icon_class = 'fa-server';
            break;
        case 'prepare':
            icon_class = 'fa-link';
            break;
        case 'configure':
            icon_class = 'fa-cog';
            break;
        case 'start':
            icon_class = 'fa-start';
            break;
        case 'stop':
            icon_class = 'fa-stop';
            break;
        case 'reset':
            icon_class = 'fa-repeat';
            break;
        default:
            icon_class = '';
    }

    return React.createElement('span', { className: 'icon-btn source-ctrl-btn fa ' + icon_class });
}

function ButtonBar(props) {
    var actions = ['describe', 'prepare', 'configure', 'start', 'stop', 'reset'];
    var buttons = actions.map(function (action) {
        return React.createElement(EccControlButton, { action: action });
    });
    return React.createElement(
        'span',
        null,
        buttons
    );
}

var ECCServerPanel = function (_React$Component2) {
    _inherits(ECCServerPanel, _React$Component2);

    function ECCServerPanel(props) {
        _classCallCheck(this, ECCServerPanel);

        var _this2 = _possibleConstructorReturn(this, (ECCServerPanel.__proto__ || Object.getPrototypeOf(ECCServerPanel)).call(this, props));

        _this2.state = {
            servers: [],
            configs: [],
            logFileModalVisible: false,
            logFileModalContent: ''
        };
        return _this2;
    }

    _createClass(ECCServerPanel, [{
        key: 'updateFromServer',
        value: function updateFromServer() {
            var _this3 = this;

            var ecc_request = $.get('/daq/api/ecc_servers');
            ecc_request.done(function (servers) {
                var promises = servers.map(function (server, index) {
                    return $.get(server.selected_config);
                });

                $.when.apply($, promises).done(function (configs) {
                    if (!$.isArray(configs)) {
                        configs = [configs];
                    }
                    _this3.setState({
                        servers: servers,
                        configs: configs
                    });
                });
            });
        }
    }, {
        key: 'componentDidMount',
        value: function componentDidMount() {
            var _this4 = this;

            this.updateFromServer();
            this.timerID = setInterval(function () {
                return _this4.updateFromServer();
            }, 5000);
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            clearInterval(this.timerID);
        }
    }, {
        key: 'showLogFileModal',
        value: function showLogFileModal(url) {
            var _this5 = this;

            $.get(url + 'log_file').done(function (response) {
                _this5.setState({
                    logFileModalVisible: true,
                    logFileModalContent: response.content
                });
            });
        }
    }, {
        key: 'hideLogFileModal',
        value: function hideLogFileModal() {
            this.setState({
                logFileModalContent: '',
                logFileModalVisible: false
            });
        }
    }, {
        key: 'render',
        value: function render() {
            var _this6 = this;

            var rows = this.state.servers.map(function (server, index) {
                var config = _this6.state.configs[index];
                var config_text = get_config_text(config);

                return React.createElement(
                    'tr',
                    { key: server.name },
                    React.createElement(
                        'td',
                        null,
                        server.name
                    ),
                    React.createElement(
                        'td',
                        null,
                        React.createElement(ECCStatusLabel, {
                            state_name: server.get_state_display,
                            is_transitioning: server.is_transitioning
                        })
                    ),
                    React.createElement(
                        'td',
                        null,
                        React.createElement('span', { className: 'icon-btn fa fa-search', onClick: function onClick() {
                                return _this6.showLogFileModal(server.url);
                            } })
                    ),
                    React.createElement(
                        'td',
                        null,
                        config_text
                    ),
                    React.createElement(
                        'td',
                        null,
                        React.createElement(ButtonBar, null)
                    )
                );
            });

            var modal = void 0;
            if (this.state.logFileModalVisible) {
                modal = React.createElement(Modal, {
                    handleHideModal: function handleHideModal() {
                        return _this6.hideLogFileModal();
                    },
                    title: 'Log file',
                    content: this.state.logFileModalContent
                });
            } else {
                modal = null;
            }

            return React.createElement(
                'div',
                { className: 'panel panel-default' },
                React.createElement(
                    'div',
                    { className: 'panel-heading' },
                    'ECC Server Status'
                ),
                React.createElement(
                    'table',
                    { className: 'table' },
                    React.createElement(
                        'thead',
                        null,
                        React.createElement(
                            'tr',
                            null,
                            React.createElement(
                                'th',
                                null,
                                'Name'
                            ),
                            React.createElement(
                                'th',
                                null,
                                'State'
                            ),
                            React.createElement(
                                'th',
                                null,
                                'Logs'
                            ),
                            React.createElement(
                                'th',
                                null,
                                'Selected Config'
                            ),
                            React.createElement(
                                'th',
                                null,
                                'Controls'
                            )
                        )
                    ),
                    React.createElement(
                        'tbody',
                        null,
                        rows
                    )
                ),
                modal
            );
        }
    }]);

    return ECCServerPanel;
}(React.Component);

ReactDOM.render(React.createElement(ECCServerPanel, null), document.getElementById('ecc-server-status-panel'));

//# sourceMappingURL=ecc_status-compiled.js.map