import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
import { hashHistory } from 'react-router';
import { connect } from 'react-redux';
var Network = require('./network');

class Login extends Component {
    constructor(props){
        super(props);
        this.state = {
            username: '', 
            password: ''
        };
        this.onSubmit = this.onSubmit.bind(this);
        this.onInput = this.onInput.bind(this);
    }

    onSubmit(e) {
        e.preventDefault();
        var data = {
            username: this.state.username,
            password: this.state.password
        };

        var me = this;
        me.props.dispatch({type: 'LOGIN_START'});
        Network.post('/api/login', null, data).done(function(d) {
            setTimeout(function () {
                //console.log(d);
                me.props.dispatch({type: 'LOGIN_GOOD', token: d.token,
                    username: data.username, userType: d.user_type});
            }, 300);
        }).fail(function(xhr) {
            setTimeout(function () {
                me.props.dispatch({type: 'LOGIN_ERROR'});
            }, 300);
        });
    }
    componentWillReceiveProps(props) {
        if(props.auth.token){
            hashHistory.push('/');
        }
    }
    componentDidMount() {
        document.body.className = 'login';
    }
    componentWillUnmount() {
        document.body.className = '';
    }
    render() {
        let status = null;
        if(this.props.auth.inProgress) {
            status = (<Bootstrap.Alert bsStyle='info'>Logging in...</Bootstrap.Alert>);
        }
        if(this.props.auth.loginError) {
            status = (<Bootstrap.Alert bsStyle='danger'>Failed logging in.</Bootstrap.Alert>);
        }

        return (
            <div id='splash-login'>
                <form onSubmit={this.onSubmit}>
                    <img src='/static/logo-splash.png' alt='VapourApps' className='splash-logo'/>
                    <Bootstrap.FormGroup controlId='username'>
                        <Bootstrap.ControlLabel>Username</Bootstrap.ControlLabel>
                        <Bootstrap.InputGroup>
                            <Bootstrap.InputGroup.Addon><Bootstrap.Glyphicon glyph="user" /></Bootstrap.InputGroup.Addon>
                            <Bootstrap.FormControl type='text' placeholder='Enter username...'
                          name='username' onChange={this.onInput} value={this.state.username} />
                        </Bootstrap.InputGroup>
                    </Bootstrap.FormGroup>

                    <Bootstrap.FormGroup controlId='password'>
                        <Bootstrap.ControlLabel>Password</Bootstrap.ControlLabel>
                        <Bootstrap.InputGroup>
                            <Bootstrap.InputGroup.Addon><Bootstrap.Glyphicon glyph="lock" /></Bootstrap.InputGroup.Addon>
                            <Bootstrap.FormControl placeholder='Enter password...' type='password'
                          name='password' onChange={this.onInput} value={this.state.password} />
                        </Bootstrap.InputGroup>
                    </Bootstrap.FormGroup>
                    <Bootstrap.FormGroup>
                    <Bootstrap.Button bsStyle='primary' type='submit' block>Log in</Bootstrap.Button>
                    </Bootstrap.FormGroup>
                </form>
                {status}
            </div>
        );
    }
    onInput(e) {
        if(e.target.name === 'username') {
            this.setState({username: e.target.value});
        } else {
            this.setState({password: e.target.value});
        }
    }
}

module.exports = connect(function(state) {
    return {auth: state.auth};
})(Login);
