var React = require('react');
var Router = require('react-router');
var Bootstrap = require('react-bootstrap');
var connect = require('react-redux').connect;

var Network = require('../network');

var Home = React.createClass({
    getInitialState: function() {
        return {
            'data': [],
            'collapse': false
        };
    },
    getPanels: function() {
        var me = this;
        Network.get('/api/panels', this.props.auth.token).done(function (data) {
            me.setState({data: data});
        }).fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    },
    componentDidMount: function() {
        if(!this.props.auth.token){
            Router.hashHistory.push('/login');
        }else{
            this.getPanels();
        }
    },
    componentWillReceiveProps: function(props) {
        if(!props.auth.token) {
            Router.hashHistory.push('/login');
        }
    },
    logOut: function (key, event) {
        if(key === 'logout')
        this.props.dispatch({type: 'LOGOUT'});
    },
    collapse: function () {
        this.setState({collapse: !this.state.collapse});
    },
    handleAlertDismiss() {
        this.props.dispatch({type: 'HIDE_ALERT'});
    },
    render: function () {
        var panels = this.state.data.filter(function(panel) {
            if(panel.instances.length > 0){
                return true;
            }
            return false;
        }).map(function(panel, i) {
            var header = (
                <span><i className={'fa ' + panel.icon} /> {panel.name} <i className='fa fa-angle-down pull-right' /></span>
            )
            var instances = panel.instances.map(function(instance) {
                var subpanels = panel.panels.admin.map(function(panel) {
                    return (
                        <li key={panel.key}><Router.Link to={'panel/' + panel.key + '/' + instance} activeClassName='active'>
                            <span>{panel.name}</span>
                        </Router.Link></li>
                    );
                });
                return (
                    <div key={instance}>
                        <span className="panels-title">{instance}</span>
                        <ul className='left-menu'>
                            {subpanels}
                        </ul>
                    </div>
                );
            });
            return (
                <Bootstrap.Panel key={panel.name} header={header} eventKey={i}>
                    {instances}
                </Bootstrap.Panel>
            );
        });

        return (
        <div>
            <Bootstrap.Navbar bsStyle='inverse'>
                <Bootstrap.Navbar.Header>
                    <Bootstrap.Glyphicon glyph='menu-hamburger' onClick={this.collapse} />
                    <img src='/static/logo.png' className='top-logo'/>
                </Bootstrap.Navbar.Header>
                <Bootstrap.Navbar.Collapse>
                    <Bootstrap.Nav pullRight={true}>
                        <Bootstrap.NavDropdown title={this.props.auth.username} onSelect={this.logOut} id="nav-dropdown">
                                <Bootstrap.MenuItem eventKey='logout'>Logout</Bootstrap.MenuItem>
                        </Bootstrap.NavDropdown>
                    </Bootstrap.Nav>
                    <Bootstrap.Nav pullRight={true}>
                        <span><i className="fa fa-bell" aria-hidden="true"></i></span>
                    </Bootstrap.Nav>
                </Bootstrap.Navbar.Collapse>
            </Bootstrap.Navbar>
            <div className='main-content'>
                <div className='sidebar' style={this.state.collapse?{left: -210}:{left: 0}}>
                    <ul className='left-menu'>
                        <li>
                        <Router.IndexLink to='' activeClassName='active'>
                        <Bootstrap.Glyphicon glyph='home' /> Overview</Router.IndexLink>
                        </li>
                        <li>
                        <Router.Link to='hosts' activeClassName='active'>
                        <Bootstrap.Glyphicon glyph='hdd' /> Hosts</Router.Link>
                        </li>
                        <li>
                        <Router.Link to='apps' activeClassName='active'>
                        <Bootstrap.Glyphicon glyph='th' /> Apps</Router.Link>
                        </li>
                        <li>
                        <Router.Link to='store' activeClassName='active'>
                        <Bootstrap.Glyphicon glyph='cloud' /> Store</Router.Link>
                        </li>
                        <li>
                        <Router.Link to='vpn' activeClassName='active'>
                            <span><i className='fa fa-lock' /> VPN</span>
                        </Router.Link>
                        </li>
                        <li role="separator" className="divider-vertical"></li>
                        <li className="panels-title">Admin panels</li>
                        <li><Bootstrap.Accordion>
                            {panels}
                        </Bootstrap.Accordion></li>
                    </ul>
                </div>
                <div className="page-content" style={this.state.collapse?{'left': '15px', 'width': '95vw'}:{'left': '230px', 'width': '80vw'}}>
                    {this.props.children}
                </div>
                {this.props.alert.show && React.createElement(Bootstrap.Alert, {bsStyle: 'danger', onDismiss: this.handleAlertDismiss, className: "messages"}, this.props.alert.msg) }
            </div>
        </div>
        );
    }
});

Home = connect(function(state) {
    return {auth: state.auth, alert: state.alert}
})(Home);

module.exports = Home;
