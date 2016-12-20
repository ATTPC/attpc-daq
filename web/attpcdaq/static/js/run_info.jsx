import React from 'react';

class RunInfoPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            experimentName: '',
            runNumber: '',
            runTitle: '',
            runType: '',
            startTime: '',
            runDuration: '',
        };
    }

    updateFromServer() {
        $.get('/daq/api/experiment').done((response) => {
            let exp = response[0];
            let run = exp.latest_run;

            if (run != null) {
                this.setState({
                    experimentName: exp.name,
                    runNumber: run.run_number,
                    runTitle: run.title,
                    runType: run.run_class,
                    startTime: run.start_datetime,
                });
            }
            else {
                this.setState({
                    experimentName: exp.name,
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
        return (
            <div className="panel panel-default">
                <div className="panel-heading">
                    <span>Run Information</span>
                    {/*<div className="pull-right">*/}
                        {/*<a className="btn btn-primary btn-xs" href="{% url 'daq/update_latest_run' %}" id="update-values-btn">*/}
                            {/*Update values*/}
                        {/*</a>*/}
                        {/*<a className="btn btn-default btn-xs" href="{% url 'daq/update_latest_run' %}?prepopulate=True"*/}
                           {/*id="same-values-btn">*/}
                            {/*Same as previous*/}
                        {/*</a>*/}
                    {/*</div>*/}
                </div>
                <table className="table">
                    <tbody>
                        <tr>
                            <th>Experiment name:</th>
                            <td>{this.state.experimentName}</td>
                        </tr>
                        <tr>
                            <th>Run number:</th>
                            <td>{this.state.runNumber}</td>
                        </tr>
                        <tr>
                            <th>Run title:</th>
                            <td>{this.state.runTitle}</td>
                        </tr>
                        <tr>
                            <th>Run type:</th>
                            <td>{this.state.runType}</td>
                        </tr>
                        <tr>
                            <th>Start time:</th>
                            <td>{this.state.startTime}</td>
                        </tr>
                        <tr>
                            <th>Current run duration:</th>
                            <td>{this.state.runDuration}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        )
    }
}

export default RunInfoPanel;