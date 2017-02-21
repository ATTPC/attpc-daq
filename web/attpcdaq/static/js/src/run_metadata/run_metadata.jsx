import React from 'react'
import $ from 'jquery'

function Panel(props) {
    return (
        <div className="panel panel-default">
            <div className="panel-heading">{props.title}</div>
            {props.table}
        </div>
    )
}

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
        return (
            <Panel title="Run information"
                   table={table}
            />
        )
    }
}

export default RunMetadataList;