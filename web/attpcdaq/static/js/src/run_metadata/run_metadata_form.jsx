import React from 'react'
import $ from 'jquery'
import { Panel } from '../panel.jsx'
import { FormInputWithLabel, FormInputGroupWithLabel, SelectWithLabel, FormButtonBar } from '../forms.jsx'

class RunMetadataForm extends React.Component {
    constructor(props) {
        super(props);

        this.apiUrl = '/daq/api/runmetadata/' + props.params.runid;

        this.state = {
            run_number: 0,
            run_class: '',
            run_class_options: [],
            title: '',
            start_datetime: '',
            stop_datetime: '',
            config_name: '',
            measurement_set: [],
        };

        const optRequest = $.ajax({
            url: this.apiUrl,
            method: 'OPTIONS',
        });

        optRequest.done((resp) => {
            const fields = resp.actions.PUT;
            this.setState({
                run_class_options: fields.run_class.choices,
            });
        });

        this.handleInputChange = this.handleInputChange.bind(this);
    }

    getCurrentValues() {
        const request = $.get(this.apiUrl);
        request.done((data) => {
            this.setState(data);
        })
    }

    componentDidMount() {
        this.getCurrentValues();
    }

    handleInputChange(event) {
        const target = event.target;
        const value = target.value;
        const name = target.name;

        this.setState({
            [name]: value,
        })
    }

    render() {
        let measurements = this.state.measurement_set;
        measurements.sort((a, b) => a.observable.order - b.observable.order);
        const form = (
            <form className="form-horizontal">
                <fieldset>
                    <legend>Run information</legend>
                    <FormInputWithLabel
                        name="run_number"
                        label="Run number"
                        inputType="number"
                        content={this.state.run_number}
                        onChange={this.handleInputChange}
                    />
                    <SelectWithLabel
                        name="run_class"
                        label="Run class"
                        options={this.state.run_class_options}
                        selectedOption={this.state.run_class}
                        onChange={this.handleInputChange}
                    />
                    <FormInputWithLabel
                        name="title"
                        label="Title"
                        content={this.state.title}
                        onChange={this.handleInputChange}
                    />
                    <FormInputWithLabel
                        name="start_datetime"
                        label="Start date/time"
                        content={this.state.start_datetime}
                        onChange={this.handleInputChange}
                    />
                    <FormInputWithLabel
                        name="stop_datetime"
                        label="Stop date/time"
                        content={this.state.stop_datetime}
                        onChange={this.handleInputChange}
                    />
                    <FormInputWithLabel
                        name="config_used"
                        label="Config name"
                        content={this.state.config_name}
                        onChange={this.handleInputChange}
                    />
                </fieldset>
                <fieldset>
                    <legend>Measurements</legend>
                    {measurements.map((meas, measIndex) => (
                        <FormInputGroupWithLabel
                            key={measIndex}
                            name={meas.observable.name}
                            content={meas.value}
                            suffix={meas.observable.units}
                            label={meas.observable.name}
                            helpText={meas.observable.comment}
                        />
                    ))}
                </fieldset>
                <FormButtonBar>
                    <input
                        className="btn btn-primary"
                        type="submit"
                        value="Submit"
                    />
                    <a className="btn btn-default">
                        Fill from last run
                    </a>
                </FormButtonBar>
            </form>
        );

        const panelBody = <div className="panel-body">{form}</div>;

        return (
            <Panel
                title="Edit run metadata"
                body={panelBody}
            />
        )
    }
}

export default RunMetadataForm;