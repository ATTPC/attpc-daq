import React from 'react';
import Cookies from 'js-cookie';
import $ from 'jquery';

function getClassName(level) {
    if (level == 'Warning') {
        return 'warning';
    }
    else if (level == 'Error') {
        return 'danger';
    }
    else if (level == 'Critical') {
        return 'danger';
    }
    else {
        return null;
    }
}

class RecentLogsPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            logs: [],
        };
    }

    updateFromServer() {
        $.get('/logs/api/log_entries/').done(response => this.setState({logs: response}));
    }

    clearAllLogs() {
        let csrf_token = Cookies.get('csrftoken');
        $.ajax({
            url: '/logs/api/log_entries/all/',
            method: 'delete',
            headers: {'X-CSRFToken': csrf_token},
        }).done(() => this.setState({logs: []}));
    }

    componentDidMount() {
        this.updateFromServer();
        this.timerID = setInterval(() => this.updateFromServer(), 5000);
    }

    componentWillUnmount() {
        clearInterval(this.timerID);
    }

    render() {
        let panelBody;
        if (this.state.logs.length == 0) {
            panelBody = <div className="panel-body">No log entries</div>;
        }
        else {
            let rows = this.state.logs.map((log, logIndex) => {
                return (
                    <tr key={log.pk} className={getClassName(log.get_level_display)}>
                        <td>{log.create_time}</td>
                        <td>{log.get_level_display}</td>
                        <td>{log.logger_name}</td>
                        <td>{log.message}</td>
                    </tr>
                );
            });

            panelBody = (
                <table className="table table-hover">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Level</th>
                            <th>Logger</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            );
        }

        return (
            <div className="panel panel-default">
                <div className="panel-heading">
                    <span>Log entries</span>
                    <div className="pull-right btn-toolbar">
                        <button className="btn btn-danger btn-xs"
                                onClick={() => this.clearAllLogs()}>
                            Clear all
                        </button>
                    </div>
                </div>
                {panelBody}
            </div>
        )
    }
}

export default RecentLogsPanel;