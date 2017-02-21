import React from 'react'
import $ from 'jquery'
import { Panel, PanelButton, PanelButtonBar } from '../panel.jsx'


function RunMetadataListEntry(props) {
    return (
        <tr>
            <td>{props.run_number}</td>
            <td>{props.get_run_class_display}</td>
            <td>{props.title}</td>
            <td>{props.config_name}</td>
            <td>{props.start_datetime}</td>
            <td>{props.stop_datetime}</td>
            <td>{props.duration_string}</td>
        </tr>
    )
}

RunMetadataListEntry.defaultProps = {
    run_type: 'None',
    get_run_class_display: 'None',
    config_name: 'None',
    start_datetime: 'None',
    stop_datetime: 'None',
    duration_string: 'None',
};

class RunMetadataList extends React.Component {
    constructor(props) {
        super(props);

        this.api_url = "/daq/api/runmetadata/";
        this.state = {
            runs: [],
        }
    }

    updateFromServer() {
        const request = $.get(this.api_url);
        request.done((data) => this.setState({runs: data}));
    }

    componentDidMount() {
        this.updateFromServer();
    }

    makeTable() {
        const rows = this.state.runs.map((run, runIndex) => {
            return <RunMetadataListEntry key={runIndex} {...run} />
        });

        return (
            <table className="table">
                <thead>
                    <tr>
                        <th>Run number</th>
                        <th>Type</th>
                        <th>Run title</th>
                        <th>Config used</th>
                        <th>Start</th>
                        <th>Stop</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        )
    }

    render() {
        const table = this.makeTable();
        const icon = <span className="fa fa-download"/>;
        const button = <PanelButton href="/daq/runs/download"
                                    label="Download as CSV"
                                    icon={icon}
                       />;
        const buttonBar = <PanelButtonBar>{button}</PanelButtonBar>;
        return (
            <Panel title="Run information"
                   body={table}
                   buttons={buttonBar}
            />
        )
    }
}

export default RunMetadataList;