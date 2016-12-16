"use strict";

class Modal extends React.Component {
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


function get_label_class(state_name) {
    if (state_name == 'Idle') {
        return 'label-idle';
    }
    else if (state_name == 'Described') {
        return 'label-described';
    }
    else if (state_name == 'Prepared') {
        return 'label-prepared';
    }
    else if (state_name == 'Ready') {
        return 'label-ready';
    }
    else if (state_name == 'Running') {
        return 'label-running';
    }
    else {
        return 'label-error';
    }
}

function ECCStatusLabel(props) {
    const state_name = props.state_name;
    const is_transitioning = props.is_transitioning;

    if (is_transitioning) {
        return (<span className="fa fa-pulse fa-spinner"></span>);
    }
    else {
        const label_class = get_label_class(state_name);
        return (
            <span className={`label ${label_class}`}>{state_name}</span>
        );
    }
}

function get_config_text(config) {
    if (config) {
        return config.describe + '/' + config.prepare + '/' + config.configure;
    }
    else {
        return ''
    }
}

function EccControlButton(props) {
    let icon_class;
    switch (props.action) {
        case 'describe':
            icon_class = 'fa-server';
            break;
        case 'prepare':
            icon_class = 'fa-link';
            break;
        case 'configure':
            icon_class = 'fa-cog';
            break;
        case 'start':
            icon_class = 'fa-start';
            break;
        case 'stop':
            icon_class = 'fa-stop';
            break;
        case 'reset':
            icon_class = 'fa-repeat';
            break;
        default:
            icon_class = '';
    }

    return (
        <span className={`icon-btn source-ctrl-btn fa ${icon_class}`}></span>
    );
}

function ButtonBar(props) {
    const actions = ['describe', 'prepare', 'configure', 'start', 'stop', 'reset'];
    const buttons = actions.map((action) => {
        return (<EccControlButton action={action}/>)
    });
    return (<span>{buttons}</span>);
}

class ECCServerPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            servers: [],
            configs: [],
            logFileModalVisible: false,
            logFileModalContent: '',
        };
    }

    updateFromServer() {
        const ecc_request = $.get('/daq/api/ecc_servers');
        ecc_request.done(servers => {
            let promises = servers.map((server, index) => $.get(server.selected_config));

            $.when.apply($, promises).done(configs => {
                if (!$.isArray(configs)) {
                    configs = [configs];
                }
                this.setState({
                    servers: servers,
                    configs: configs,
                });
            });
        });
    }

    componentDidMount() {
        this.updateFromServer();
        this.timerID = setInterval(() => this.updateFromServer(), 5000);
    }

    componentWillUnmount() {
        clearInterval(this.timerID);
    }

    showLogFileModal(url) {
        $.get(url + 'log_file').done(response => {
            this.setState({
                logFileModalVisible: true,
                logFileModalContent: response.content,
            });
        });
    }

    hideLogFileModal() {
        this.setState({
            logFileModalContent: '',
            logFileModalVisible: false,
        });
    }

    render() {
        const rows = this.state.servers.map((server, index) => {
            const config = this.state.configs[index];
            const config_text = get_config_text(config);

            return (
                <tr key={server.name}>
                    <td>{server.name}</td>
                    <td>
                        <ECCStatusLabel
                            state_name={server.get_state_display}
                            is_transitioning={server.is_transitioning}
                        />
                    </td>
                    <td>
                        <span className="icon-btn fa fa-search" onClick={() => this.showLogFileModal(server.url)}></span>
                    </td>
                    <td>{config_text}</td>
                    <td><ButtonBar /></td>
                </tr>
            )
        });

        let modal;
        if (this.state.logFileModalVisible) {
            modal = <Modal
                handleHideModal={() => this.hideLogFileModal()}
                title="Log file"
                content={this.state.logFileModalContent}
            />;
        }
        else {
            modal = null;
        }

        return (
            <div className="panel panel-default">
                <div className="panel-heading">ECC Server Status</div>
                <table className="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>State</th>
                            <th>Logs</th>
                            <th>Selected Config</th>
                            <th>Controls</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                {modal}
            </div>
        )
    }
}

ReactDOM.render(
    <ECCServerPanel/>,
    document.getElementById('ecc-server-status-panel')
);