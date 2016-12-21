import React from 'react';
import {getStateBgColor, getStateIcon} from './components.jsx';
import $ from 'jquery';

class SystemStatusPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = ({
            overallState: 'Idle',
        });
    }

    updateFromServer() {
        $.get('/daq/api/ecc_servers/overall_state/').done((response) => {
            if (response.success) {
                this.setState({
                    overallState: response.overall_state_name,
                });
            }
        });
    }

    componentDidMount() {
        this.updateFromServer();
        this.timerID = setInterval(() => this.updateFromServer(), 5000);
    }

    componentWillUnmount() {
        clearInterval(this.timerID);
    }

    render() {
        const iconClass = getStateIcon(this.state.overallState);
        const bgColorClass = getStateBgColor(this.state.overallState);

        return (
            <div className={`panel panel-status ${bgColorClass}`}>
                <span className="status-icon">
                    <span className={`fa ${iconClass}`}></span>
                </span>
                <span className="status-text">{this.state.overallState}</span>
            </div>
        )
    }
}

export default SystemStatusPanel;