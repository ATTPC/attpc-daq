import React from 'react';
import ReactDOM from 'react-dom';
import $ from 'jquery';

export class Modal extends React.Component {
    componentDidMount(){
        let $node = $(ReactDOM.findDOMNode(this));
        $node.modal('show');
        $node.on('hidden.bs.modal', this.props.handleHideModal);
    }

    render(){
        return (
          <div className="modal fade">
            <div className="modal-dialog modal-lg">
              <div className="modal-content">
                <div className="modal-header">
                  <button type="button" className="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                  <h4 className="modal-title">{this.props.title}</h4>
                </div>
                <div className="modal-body">
                  <pre>{this.props.content}</pre>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-default" data-dismiss="modal">Close</button>
                </div>
              </div>
            </div>
          </div>
        )
    }
}

export function getActionIcon(action) {
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

export function getStateIcon(state) {
    if (state == 'Idle') {
        return 'fa-power-off';
    }
    else if (state == 'Described') {
        return 'fa-server';
    }
    else if (state == 'Prepared') {
        return 'fa-link';
    }
    else if (state == 'Ready') {
        return 'fa-check-circle';
    }
    else if (state == 'Running') {
        return 'fa-play';
    }
    else {
        return 'fa-warning';
    }
}

export function getStateBgColor(state) {
    if (state == 'Idle') {
        return 'bg-color-idle';
    }
    else if (state == 'Described') {
        return 'bg-color-described';
    }
    else if (state == 'Prepared') {
        return 'bg-color-prepared';
    }
    else if (state == 'Ready') {
        return 'bg-color-ready';
    }
    else if (state == 'Running') {
        return 'bg-color-running';
    }
    else {
        return 'bg-color-error';
    }
}

export function getStateLabelClass(state) {
    if (state == 'Idle') {
        return 'label-idle';
    }
    else if (state == 'Described') {
        return 'label-described';
    }
    else if (state == 'Prepared') {
        return 'label-prepared';
    }
    else if (state == 'Ready') {
        return 'label-ready';
    }
    else if (state == 'Running') {
        return 'label-running';
    }
    else {
        return 'label-error';
    }
}