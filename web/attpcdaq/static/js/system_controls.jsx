import React from 'react';
import Cookies from 'js-cookie';

function getActionIcon(action) {
    if (action == 'describe') {
        return 'fa-server';
    }
    else if (action == 'prepare') {
        return 'fa-link';
    }
    else if (action == 'configure') {
        return 'fa-cog';
    }
    else if (action == 'start') {
        return 'fa-play';
    }
    else if (action == 'stop') {
        return 'fa-stop';
    }
    else if (action == 'reset') {
        return 'fa-repeat';
    }
    else {
        console.error('Unknown action: ' + action);
        return 'fa-question';
    }
}

function getButtonClass(action) {
    if (action == 'describe') {
        return 'btn-describe';
    }
    else if (action == 'prepare') {
        return 'btn-prepare';
    }
    else if (action == 'configure') {
        return 'btn-configure';
    }
    else if (action == 'start') {
        return 'btn-start';
    }
    else if (action == 'stop') {
        return 'btn-stop';
    }
    else if (action == 'reset') {
        return 'btn-reset';
    }
    else {
        console.error('Unknown action: ' + action);
        return 'btn-default';
    }
}

class SystemControlButton extends React.Component {
    doStateTransition() {
        const csrf_token = Cookies.get('csrftoken');
        $.post({
            url: '/daq/api/ecc_servers/' + this.props.action + '/',
            headers: {'X-CSRFToken': csrf_token},
        });
    }

    render() {
        const icon_class = getActionIcon(this.props.action);
        const btn_class = getButtonClass(this.props.action);
        const text = this.props.action.charAt(0).toUpperCase() + this.props.action.slice(1) + " all";

        const icon = <span className={`fa ${icon_class}`}></span>;

        return (
            <button className={`btn btn-block ${btn_class}`}
                onClick={() => this.doStateTransition()}>
                {icon} {text}
            </button>
        )
    }
}

export class SystemControlPanel extends React.Component {
    render() {
        return (
            <div className="panel panel-default">
                <div className="panel-heading">
                    Controls
                </div>
                <div className="panel-body">
                    <div className="btn-toolbar">
                        <SystemControlButton action="describe"/>
                        <SystemControlButton action="prepare"/>
                        <SystemControlButton action="configure"/>
                        <SystemControlButton action="start"/>
                        <SystemControlButton action="stop"/>
                        <SystemControlButton action="reset"/>
                    </div>
                </div>
            </div>
        )
    }
}