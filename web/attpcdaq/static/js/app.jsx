import React from 'react'
import { Router, Route, Link, IndexRoute, useRouterHistory } from 'react-router'
import { render } from 'react-dom'
import { createHistory } from 'react-router/node_modules/history'

import StatusPage from './status_page.jsx';

const history = useRouterHistory(createHistory)({
    basename: '/daq'
});

render((
    <Router history={history}>
        <Route path="/status" component={StatusPage}>
        </Route>
    </Router>
), document.getElementById('status-page-app'));