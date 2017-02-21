import React from 'react'

export function FormInputWithLabel(props) {
    const inputId = 'input_' + props.name;
    return (
        <div className="form-group">
            <label htmlFor={inputId} className="col-lg-2 control-label">
                {props.label}
            </label>
            <div className="col-lg-8">
                <input
                    className="form-control"
                    id={inputId}
                    name={props.name}
                    type={props.inputType}
                    value={props.content}
                    onChange={props.onChange}
                    placeholder={props.placeholder}
                />
            </div>
        </div>
    )
}

FormInputWithLabel.defaultProps = {
    content: '',
    inputType: 'text',
};

export function FormInputGroupWithLabel(props) {
    const inputId = 'input_' + props.name;
    return (
        <div className="form-group">
            <label htmlFor={inputId} className="col-lg-2 control-label">
                {props.label}
            </label>
            <div className="col-lg-8">
                <div className="input-group">
                    <input
                        className="form-control"
                        id={inputId}
                        name={props.name}
                        type={props.inputType}
                        value={props.content}
                        onChange={props.onChange}
                        placeholder={props.placeholder}
                    />
                    <span className="input-group-addon">{props.suffix}</span>
                </div>
                {props.helpText !== '' ? <p className="help-block">{props.helpText}</p> : ''}
            </div>
        </div>
    )
}

FormInputGroupWithLabel.defaultProps = {
    content: '',
    suffix: '',
    helpText: '',
};

export function SelectWithLabel(props) {
    const inputId = 'input_' + props.name;

    const options = props.options.map(opt => {
        return <option key={opt.value} value={opt.value}>{opt.display_name}</option>
    });

    return (
        <div className="form-group">
            <label htmlFor={inputId} className="col-lg-2 control-label">
                {props.label}
            </label>
            <div className="col-lg-8">
                <select
                    className="form-control"
                    id={inputId}
                    name={props.name}
                    value={props.selectedOption}
                    onChange={props.onChange}>
                    <option value="">{props.placeholder}</option>
                    {options}
                </select>
            </div>
        </div>
    )
}

SelectWithLabel.defaultProps = {
    content: '',
    options: [],
    placeholder: '---'
};

export function FormButtonBar(props) {
    return (
        <div className="form-group">
            <div className="col-lg-2"></div>
            <div className="col-lg-8 btn-toolbar">
                {props.children}
            </div>
        </div>
    )
}