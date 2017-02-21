import React from 'react'

export function Panel(props) {
    return (
        <div className="panel panel-default">
            <div className="panel-heading">
                {props.title}
                {props.buttons}
            </div>
            {props.body}
        </div>
    )
}

Panel.defaultProps = {
    title: 'Panel',
    body: '',
};

export function PanelButtonBar(props) {
    return (
        <div className="pull-right">
            {props.children}
        </div>
    )
}

export function PanelButton(props) {
    return (
        <a className="btn btn-default btn-xs" href={props.href}>
            {props.icon} {props.label}
        </a>
    )
}

PanelButton.defaultProps = {
    href: '#',
    label: 'Button',
};