import React from "react";
import {Modal} from "../components.jsx";
import $ from 'jquery';


function StatusIndicator(props) {
    let iconClass;
    let colorClass;
    if (props.isGood) {
        iconClass = "fa-check-circle";
        colorClass = "text-success";
    }
    else {
        iconClass = "fa-times-circle";
        colorClass = "text-danger";
    }
    return (
        <span className={`fa ${iconClass} ${colorClass}`}></span>
    );
}

class DataRouterPanel extends React.Component
{
    constructor() {
        super();
        this.state = {
            routers: [],
            logFileModalVisible: false,
            logFileModalContent: '',
        };
    }

    getRouterList() {
        $.get('/daq/api/data_routers').done(data => {
            this.setState({
                routers: data,
            });
        });
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

    componentDidMount() {
        this.getRouterList();
        this.timerID = setInterval(() => this.getRouterList(), 5000);
    }

    componentWillUnmount() {
        clearInterval(this.timerID);
    }

    render() {
        const rows = this.state.routers.map((router, index) => {
            return (
                <tr key={router.name}>
                    <td>{router.name}</td>
                    <td><StatusIndicator isGood={router.is_online}/></td>
                    <td><StatusIndicator isGood={router.staging_directory_is_clean}/></td>
                    <td><span className="icon-btn fa fa-search" onClick={() => this.showLogFileModal(router.url)}></span></td>
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
                <div className="panel-heading">Data Router Status</div>
                <table className="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Online</th>
                            <th>Clean</th>
                            <th>Logs</th>
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

export default DataRouterPanel;