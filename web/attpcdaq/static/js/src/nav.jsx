import React from 'react'
import { Link } from 'react-router'
import $ from 'jquery'

export function SideNavbarItem(props) {
    const isActive = props.isActive || false;
    const activeClass = isActive ? 'active' : '';
    return (
        <li className={activeClass}>
            <Link to={props.href} activeClassName="active">
                <span className={`fa ${props.iconClass}`}/> {props.name}
            </Link>
        </li>
    )
}

export function SideNavbar(props) {
    return (
        <div className="col-sm-3 col-md-2 sidebar">
            <div className="sidebar-app-name">AT-TPC DAQ</div>
            <ul className="nav nav-sidebar">
                {props.children}
            </ul>
        </div>
    )
}

export class TopNavbar extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            username: 'Unknown',
            experimentName: 'Unknown',
        };
        this.api_url = '/daq/api/experiment';
    }

    componentDidMount() {
        const request = $.get(this.api_url);
        request.done((response) => {
            const expt = response[0];
            this.setState({
                username: expt.user.username,
                experimentName: expt.name,
            })
        });
    }

    render() {
        return (
            <div className="navbar navbar-default">
                <ul className="nav navbar-nav pull-right">
                    <li>
                        <a><span className="fa fa-user"/>{` ${this.state.username} (${this.state.experimentName})`}</a>
                    </li>
                    <li>
                        <a href="/doc" target="_blank"><span className="fa fa-question-circle"/> Help</a>
                    </li>
                    <li><a href="accounts/logout"><span className="fa fa-sign-out"/> Log out</a></li>
                </ul>
            </div>
        )
    }
}
