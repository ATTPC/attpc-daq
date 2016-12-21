"use strict";
import React from 'react';
import {Modal, getStateLabelClass, getActionIcon} from "./components.jsx";
import Cookies from "js-cookie";
import $ from 'jquery';


function ECCStatusLabel(props) {
    const state_name = props.state_name;
    const is_transitioning = props.is_transitioning;

    if (is_transitioning) {
        return (<span className="fa fa-pulse fa-spinner"></span>);
    }
    else {
        const label_class = getStateLabelClass(state_name);
        return (
            <span className={`label ${label_class}`}>{state_name}</span>
        );
    }
}

function get_config_text(config) {
    if (config) {
        return config.describe + '/' + config.prepare + '/' + config.configure;
    }
    else {
        return ''
    }
}

function EccControlButton(props) {
    const icon_class = getActionIcon(props.action);
    return (
        <span className={`icon-btn source-ctrl-btn fa ${icon_class}`} onClick={() => props.onClick()}></span>
    );
}

class ECCServerPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            servers: [],
            configs: [],
            logFileModalVisible: false,
            logFileModalContent: '',
        };
    }

    updateFromServer() {
        const ecc_request = $.get('/daq/api/ecc_servers');
        ecc_request.done(servers => {
            let promises = servers.map((server, index) => $.get(server.selected_config));

            $.when.apply($, promises).done(configs => {
                if (!$.isArray(configs)) {
                    configs = [configs];
                }
                this.setState({
                    servers: servers,
                    configs: configs,
                });
            });
        });
    }

    doStateTransition(serverIndex, transitionName) {
        const csrf_token = Cookies.get('csrftoken');
        const server = this.state.servers[serverIndex];
        $.post({
            url: server.url + transitionName + '/',
            headers: {'X-CSRFToken': csrf_token}
        }).done(() => this.updateFromServer());
    }

    componentDidMount() {
        this.updateFromServer();
        this.timerID = setInterval(() => this.updateFromServer(), 5000);
    }

    componentWillUnmount() {
        clearInterval(this.timerID);
    }

    showLogFileModal(url) {
        $.get(url + 'log_file').done(response => {
            this.setState({
                logFileModalVisible: true,
                logFileModalContent: response.content,
            });
        });
    }

    hideLogFileModal() {
        this.setState({
            logFileModalContent: '',
            logFileModalVisible: false,
        });
    }

    render() {
        const rows = this.state.servers.map((server, serverIndex) => {
            const config = this.state.configs[serverIndex];
            const config_text = get_config_text(config);

            const ecc_actions = ['describe', 'prepare', 'configure', 'start', 'stop', 'reset'];
            const buttons = ecc_actions.map((action, actionIndex) => {
                return (
                    <td key={action} width="35px">
                        <EccControlButton
                            action={action}
                            onClick={() => this.doStateTransition(serverIndex, action)}
                        />
                    </td>
                )
            });

            return (
                <tr key={server.name}>
                    <td>{server.name}</td>
                    <td>
                        <ECCStatusLabel
                            state_name={server.get_state_display}
                            is_transitioning={server.is_transitioning}
                        />
                    </td>
                    <td>
                        <span className="icon-btn fa fa-search" onClick={() => this.showLogFileModal(server.url)}></span>
                    </td>
                    <td>{config_text}</td>
                    {buttons}
                </tr>
            )
        });

        let modal;
        if (this.state.logFileModalVisible) {
            modal = <Modal
                handleHideModal={() => this.hideLogFileModal()}
                title="Log file"
                content={this.state.logFileModalContent}
            />;
        }
        else {
            modal = null;
        }

        return (
            <div className="panel panel-default">
                <div className="panel-heading">ECC Server Status</div>
                <table className="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>State</th>
                            <th>Logs</th>
                            <th>Selected Config</th>
                            <th colSpan="6">Controls</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                {modal}
            </div>
        )
    }
}

export default ECCServerPanel;
