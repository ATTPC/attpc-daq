"use strict";

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

function StatusIndicator(props) {
    var iconClass = void 0;
    var colorClass = void 0;
    if (props.isGood) {
        iconClass = "fa-check-circle";
        colorClass = "text-success";
    } else {
        iconClass = "fa-times-circle";
        colorClass = "text-danger";
    }
    return React.createElement("span", { className: "fa " + iconClass + " " + colorClass });
}

var DataRouterPanel = function (_React$Component) {
    _inherits(DataRouterPanel, _React$Component);

    function DataRouterPanel() {
        _classCallCheck(this, DataRouterPanel);

        var _this = _possibleConstructorReturn(this, (DataRouterPanel.__proto__ || Object.getPrototypeOf(DataRouterPanel)).call(this));

        _this.state = {
            routers: []
        };
        return _this;
    }

    _createClass(DataRouterPanel, [{
        key: "getRouterList",
        value: function getRouterList() {
            var _this2 = this;

            $.get('/daq/api/data_routers').done(function (data) {
                _this2.setState({
                    routers: data
                });
            });
        }
    }, {
        key: "componentDidMount",
        value: function componentDidMount() {
            var _this3 = this;

            this.getRouterList();
            this.timerID = setInterval(function () {
                return _this3.getRouterList();
            }, 5000);
        }
    }, {
        key: "componentWillUnmount",
        value: function componentWillUnmount() {
            clearInterval(this.timerID);
        }
    }, {
        key: "render",
        value: function render() {
            var rows = this.state.routers.map(function (router, index) {
                return React.createElement(
                    "tr",
                    { key: router.name },
                    React.createElement(
                        "td",
                        null,
                        router.name
                    ),
                    React.createElement(
                        "td",
                        null,
                        React.createElement(StatusIndicator, { isGood: router.is_online })
                    ),
                    React.createElement(
                        "td",
                        null,
                        React.createElement(StatusIndicator, { isGood: router.staging_directory_is_clean })
                    ),
                    React.createElement(
                        "td",
                        null,
                        "Link"
                    )
                );
            });
            return React.createElement(
                "div",
                { className: "panel panel-default" },
                React.createElement(
                    "div",
                    { className: "panel-heading" },
                    "Data Router Status"
                ),
                React.createElement(
                    "table",
                    { className: "table" },
                    React.createElement(
                        "thead",
                        null,
                        React.createElement(
                            "tr",
                            null,
                            React.createElement(
                                "th",
                                null,
                                "Name"
                            ),
                            React.createElement(
                                "th",
                                null,
                                "Online"
                            ),
                            React.createElement(
                                "th",
                                null,
                                "Clean"
                            ),
                            React.createElement(
                                "th",
                                null,
                                "Logs"
                            )
                        )
                    ),
                    React.createElement(
                        "tbody",
                        null,
                        rows
                    )
                )
            );
        }
    }]);

    return DataRouterPanel;
}(React.Component);

ReactDOM.render(React.createElement(DataRouterPanel, null), document.getElementById('data-router-status-panel'));

//# sourceMappingURL=statuspage-compiled.js.map