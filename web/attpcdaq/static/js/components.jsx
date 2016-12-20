import React from 'react';
import ReactDOM from 'react-dom';

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
