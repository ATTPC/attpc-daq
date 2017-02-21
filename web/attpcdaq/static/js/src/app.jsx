import React from 'react'
import { Router, Route, Link, IndexRoute, useRouterHistory } from 'react-router'
import { render } from 'react-dom'
import { createHistory } from 'react-router/node_modules/history'

import StatusPage from './status/status_page.jsx'
import RunMetadataList from './run_metadata/run_metadata.jsx'
import { SideNavbar, SideNavbarItem, TopNavbar } from './nav.jsx'

class App extends React.Component {
    render() {
        return (
            <div className="container-fluid">
                <div className="row">
                    <SideNavbar>
                        <SideNavbarItem name="Status"
                                        href="status"
                                        iconClass="fa-home"
                                        isActive={false}
                        />
                        <SideNavbarItem name="Run metadata"
                                        href="runs"
                                        iconClass="fa-list-alt"
                                        isActive={false}
                        />
                    </SideNavbar>
                    <div className="col-sm-9 col-sm-offset-3 col-md-10 col-md-offset-2">
                        <TopNavbar/>
                        {this.props.children}
                    </div>
                </div>
            </div>
        )
    }
}

const history = useRouterHistory(createHistory)({
    basename: '/daq/app'
});

render((
    <Router history={history}>
        <Route path="/" component={App}>
            <IndexRoute component={StatusPage} />
            <Route path="/status" component={StatusPage}/>
            <Route path="/runs" component={RunMetadataList}/>
        </Route>
    </Router>
), document.getElementById('app-mount'));