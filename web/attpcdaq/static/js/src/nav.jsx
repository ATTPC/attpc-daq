import React from 'react'
import { Link } from 'react-router'

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

export function TopNavbar(props) {
    return (
        <div className="navbar navbar-default">
            <ul className="nav navbar-nav pull-right">
                <li><span className="fa fa-user"/>{` ${props.username} (${props.experiment_name})`}</li>
                <li>
                    <a href="/doc" target="_blank"><span className="fa fa-question-circle"/> Help</a>
                </li>
                <li><a href="accounts/logout">Log out</a></li>
            </ul>
        </div>
    )
}



// <div class="container-fluid">
//         <div class="row">
//
//             <div class="col-sm-9 col-sm-offset-3 col-md-10 col-md-offset-2">

//
//                 <div id="app-mount"></div>
//                 <script src="{% static 'js/build/app.js' %}"></script>
//             </div>