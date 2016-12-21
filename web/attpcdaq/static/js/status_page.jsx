import React from 'react';
import ReactDOM from 'react-dom';
import ECCServerPanel from './ecc_status.jsx';
import DataRouterPanel from './data_router_status.jsx';
import RunInfoPanel from './run_info.jsx';
import SystemControlPanel from './system_controls.jsx';
import SystemStatusPanel from './system_status.jsx';
import RecentLogsPanel from './recent_logs.jsx';

class StatusPageApp extends React.Component {
    render() {
        return (
            <div className="row">
                <div className="col-md-9">
                    <RunInfoPanel/>
                    <ECCServerPanel/>
                    <DataRouterPanel/>
                    <RecentLogsPanel/>
                </div>
                <div className="col-md-3">
                    <SystemStatusPanel/>
                    <SystemControlPanel/>
                </div>
            </div>
        )
    }
}

ReactDOM.render(
    <StatusPageApp/>,
    document.getElementById('status-page-app')
);