import React from 'react';

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
        $.get('/logs/api/recent_logs/').done(response => this.setState({logs: response}));
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
                </div>
                {panelBody}
            </div>
        )
    }
}

export default RecentLogsPanel;