import React from 'react';
import ReactDOM from 'react-dom';
import {ECCServerPanel} from './ecc_status.jsx'
import {DataRouterPanel} from './data_router_status.jsx'
import {RunInfoPanel} from './run_info.jsx'

ReactDOM.render(
    <ECCServerPanel/>,
    document.getElementById('ecc-server-status-panel')
);

ReactDOM.render(
    <DataRouterPanel />,
    document.getElementById('data-router-status-panel')
);

ReactDOM.render(
    <RunInfoPanel/>,
    document.getElementById('run-info-panel')
);