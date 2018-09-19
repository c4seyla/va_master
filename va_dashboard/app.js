import React, { Component } from 'react';
import {render} from 'react-dom';
import {Router, Route, IndexRoute, hashHistory} from 'react-router';
import {combineReducers, createStore} from 'redux';
import {connect, Provider} from 'react-redux';
import FontFaceObserver from 'fontfaceobserver';
var Network = require('./network');


function auth(state, action){
    if(typeof state === 'undefined'){
        var storageState = window.localStorage.getItem('auth'); // Check session
        if(storageState !== null) {
            return JSON.parse(storageState);
        } else {
            return {token: null, username: null, loginError: false, inProgress: false};
        }
    }

    var newState = Object.assign({}, state);
    if(action.type == 'LOGIN_START' || action.type === 'LOGOUT' || action.type == 'LOGIN_ERROR'){
        newState.username = null;
        newState.token = null;
        newState.loginError = false;
        newState.inProgress = false;
    }
    if(action.type === 'LOGIN_START') newState.inProgress = true;
    if(action.type === 'LOGIN_ERROR') newState.loginError = true;
    if(action.type === 'LOGIN_GOOD') {
        newState.username = action.username;
        newState.token = action.token;
        newState.loginError = false;
        newState.inProgress = false;
    }
    // Add into session
    window.localStorage.setItem('auth', JSON.stringify(newState));
    return newState;
}

function menu(state, action){
    if(typeof state === 'undefined'){
        return {tabs: {vpn: [
            {title: 'Status', link: 'vpn_status'},
            {title: 'Users', link: 'vpn_users'}
        ], users: [
            {title: 'Users', link: 'users_users'},
            {title: 'Groups', link: 'users_groups'}
        ] }, showTabs: false, selectedTab: -1};
    }
    var newState = Object.assign({}, state);

    if(action.type == 'ADD_TABS'){
        newState.tabs[action.key] = action.tabs;
        newState.selectedTab = 0;
        newState.showTabs = action.key;
    }
    else if(action.type == 'RESET_TABS'){
        //newState.tabs[action.key] = [];
        newState.showTabs = false;
        newState.selectedTab = -1;
    }
    else if(action.type == 'SELECT_TAB'){
        newState.selectedTab = action.index;
    }
    else if(action.type == 'SHOW_TABS'){
        newState.showTabs = action.key;
    }
    return newState;
}

function table(state, action){
    if(typeof state === 'undefined'){
        return {};
    }
    var newState = Object.assign({}, state);

    if(action.type == 'ADD_DATA'){
        newState = action.tables;
        // newState.path = [];
    }
    else if(action.type == 'CHANGE_DATA'){
        newState[action.name] = action.data;
        if("passVal" in action){
            newState["path"].push(action.passVal);
        }else if("initVal" in action){
            newState["path"] = action.initVal;
        }
    }
    else if(action.type == 'CHANGE_MULTI_DATA'){
        for(let key in action.data){
            newState[key] = action.data[key];
        }
    }
    return newState;
}

function filter(state, action){
    if(typeof state === 'undefined'){
        return {filterBy: ""};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'FILTER'){
        newState.filterBy = action.filterBy;
    }
    if(action.type == 'RESET_FILTER'){
        newState.filterBy = "";
    }

    return newState;
}

function modal(state, action){
    if(typeof state === 'undefined'){
        return {isOpen: false, template: { title: "", content: [], buttons: [], args: [], kwargs: {}}, args: {}, modalType: "", rowIndex: ''};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'OPEN_MODAL'){
        if("template" in action)
            newState.template = action.template;
        if("args" in action){
            newState.args = action.args;
        }
        if("modalType" in action){
            newState.modalType = action.modalType;
        }
        if("rowIndex" in action){
            newState.rowIndex = action.rowIndex;
        }
        if("kwargs" in action){
            newState.kwargs = action.kwargs;
        }
        newState.isOpen = true;
    }
    if(action.type == 'CLOSE_MODAL'){
        newState.template = { title: "", content: [], buttons: [], args: [], kwargs: {}};
        newState.args = {};
        newState.isOpen = false;
        newState.modalType = "";
        newState.rowIndex = "";
    }

    return newState;
}

function apps(state, action){
    if(typeof state === 'undefined'){
        return {select: "-1"};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'LAUNCH'){
        newState.select = action.select;
    }
    if(action.type == 'RESET_APP'){
        newState.select = "-1";
    }

    return newState;
}

function div(state, action){
    if(typeof state === 'undefined'){
        return {show: 'hidden'};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'TOGGLE'){
        newState.show = newState.show ? '':'hidden';
    }

    return newState;
}

function panel(state, action){
    if(typeof state === 'undefined'){
        return {panel: '', server: '', args: ''};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'CHANGE_PANEL'){
        newState.panel = action.panel;
        newState.server = action.server;
        if('args' in action){
            newState.args = action.args;
        }else{
            newState.args = "";
        }
    }

    return newState;
}

function alert(state, action){
    if(typeof state === 'undefined'){
        return {msg: '', show: false, className: ''};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'SHOW_ALERT'){
        newState.msg = action.msg;
        newState.show = true;
        newState.className = action.success ? 'success' : 'danger';
    }
    if(action.type == 'HIDE_ALERT'){
        newState.msg = '';
        newState.show = false;
    }

    return newState;
}

function form(state, action){
    if(typeof state === 'undefined'){
        return {readonly: {}, dropdowns: {}};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'SET_READONLY'){
        newState.readonly = action.readonly;
    }
    if(action.type == 'RESET_FORM'){
        newState.readonly = {};
    }
    if(action.type == 'ADD_DROPDOWN'){
        newState.dropdowns = action.dropdowns;
    }
    if(action.type == 'SELECT'){
        newState.dropdowns[action.name].select = action.select;
    }
    if(action.type == 'RESET_SELECTION'){
        newState.dropdowns[action.name].select = "";
    }

    return newState;
}

function sidebar(state, action){
    if(typeof state === 'undefined'){
        return {collapsed: 0};
    }

    var newState = Object.assign({}, state);
    if(action.type == 'COLLAPSE'){
        newState.collapsed = 1;
    }
    if(action.type == 'RESET_COLLAPSE'){
        newState.collapsed = 0;
    }

    return newState;
}

let ws;

function initSocket() {
    var host = window.location.host;
    if(host.indexOf(":") == 0){
        host += ":80";
    }
    var protocol =  window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${protocol}://${host}/log`);
    ws.onmessage = evt => {
        var data = JSON.parse(evt.data);
        var logs = [], hosts = [];
        if(data.type === "update"){
          store.dispatch({type: 'UPDATE_LOGS', log: data.message, host: data.message.host })
        }
        else if(data.type === "init"){
          logs = data.logs, hosts = data.hosts;
          store.dispatch({type: 'INIT_LOGS', logs, hosts, selected_hosts: hosts })
        }
        else if(data.type === "init_notifications"){
          store.dispatch({type: 'INIT_NOTIFICATIONS', notifications: data.notifications })
        }
        else if(data.type === "update_notifications"){
          store.dispatch({type: 'UPDATE_NOTIFICATIONS', notification: {message: data.message, timestamp: data.timestamp, severity: data.severity, host: data.host} })
        }
    };
    ws.onerror = evt => {
        ws.close();
        store.dispatch({type: 'SHOW_ALERT', msg: "Socket error."});
    };
}

initSocket()

function logs(state, action){
    if(typeof state === 'undefined'){
        return {
          logs: [],
          newLogs: 0
        };
    }

    var newState = Object.assign({}, state);
    if(action.type == 'INIT_LOGS'){
      newState.logs = action.logs;
      newState.newLogs = 0;
    }
    else if(action.type == 'UPDATE_LOGS'){
      newState.logs = [...newState.logs, action.log];
      ++newState.newLogs;
    }
    else if(action.type == 'RESET_LOGS'){
      newState.logs = [];
      newState.newLogs = 0;
    }
    else if(action.type == 'SEND_MESSAGE') {
      ws.send(JSON.stringify(action.msg));
    }
    else if(action.type == 'GET_LOGS'){
      if(ws.readyState === ws.OPEN){
        ws.send(JSON.stringify({type: "get_messages"}));
      } else {
        setTimeout(() => ws.send(JSON.stringify({type: "get_messages"})), 1000)
      }
    }

    return newState;
}

function hosts(state, action){
    if(typeof state === 'undefined'){
        return {
          hosts: [],
          selected_hosts: []
        };
    }

    var newState = Object.assign({}, state);
    if(action.type == 'INIT_LOGS'){
      newState.hosts = action.hosts;
      newState.selected_hosts = action.selected_hosts;
    }
    else if(action.type == 'UPDATE_LOGS'){
      let h = newState.hosts.map((host) => host.value);
      if(h.indexOf(action.host) === -1){
        newState.hosts = [...newState.hosts, {value: action.host, label: action.host}];
        newState.selected_hosts = Object.assign([], newState.hosts);
      }
    }
    else if(action.type == 'SELECT_HOST'){
      newState.selected_hosts = action.selected_hosts;
    }

    return newState;
}

function notifications(state, action){
    if(typeof state === 'undefined'){
        return {
          notifications: [],
          newNotifications: []
        };
    }

    var newState = Object.assign({}, state);
    if(action.type == 'INIT_NOTIFICATIONS'){
      newState.notifications = action.notifications;
      newState.notifications.reverse();
      newState.newNotifications = [];
    }
    else if(action.type == 'UPDATE_NOTIFICATIONS'){
      // newState.notifications = [action.notification, ...newState.notifications];
      // ++newState.newNotifications;
      newState.newNotifications = [action.notification, ...newState.newNotifications];
    }
    else if(action.type == 'READ_ALL_NOTIFICATIONS'){
      // newState.newNotifications = 0;
      newState.notifications = [...Object.assign([], newState.newNotifications), ...newState.notifications];
      newState.newNotifications = [];
    }

    return newState;
}

var mainReducer = combineReducers({auth, table, filter, modal, apps, div, panel, alert, form, sidebar, logs, hosts, notifications, menu});
var store = createStore(mainReducer);

var Home = require('./tabs/home');
var Overview = require('./tabs/overview');
var Providers = require('./tabs/providers');
var Servers = require('./tabs/servers');
var Store = require('./tabs/store');
var Panel = require('./tabs/panel');
var Subpanel = require('./tabs/subpanel');
var Vpn = require('./tabs/vpn');
var VpnUsers = require('./tabs/vpn_users');
var VpnStatus = require('./tabs/vpn_status');
var VpnLogins = require('./tabs/vpn_logins');
var ChartPanel = require('./tabs/chart_panel');
var Triggers = require('./tabs/triggers');
var Ts_status = require('./tabs/ts_status');
var Log = require('./tabs/log');
var Billing = require('./tabs/billing');
var Services = require('./tabs/services');
var Users = require('./tabs/users').Panel;
var Groups = require('./tabs/users_groups');

var Login = require('./login');
class App extends Component {
  render() {
    return (
        <Router history={hashHistory}>
            <Route path='/' component={Home} onChange={() => store.dispatch({type: 'HIDE_ALERT'})}>
                <IndexRoute component={Overview} />
                <Route path='/providers' component={Providers} />
                <Route path='/servers' component={Servers} />
                <Route path='/store' component={Store} />
                <Route path='/vpn' component={Vpn} />
                <Route path='/vpn_status' component={VpnStatus} />
                <Route path='/vpn_users' component={VpnUsers} />
                <Route path='/vpn/list_logins/:username' component={VpnLogins} />
                <Route path='/triggers' component={Triggers} />
                <Route path='/ts_status' component={Ts_status} />
                <Route path='/log(/:type)' component={Log} />
                <Route path='/billing' component={Billing} />
                <Route path='/services' component={Services} />
                <Route path='/users_users' component={Users} />
                <Route path='/users_groups' component={Groups} />
                <Route path='/panel/:id/:server(/:args)' component={Panel} />
                <Route path='/subpanel/:id/:server/:args' component={Subpanel} />
                <Route path='/chart_panel/:server/:provider/:service' component={ChartPanel} />
            </Route>
            <Route path='/login' component={Login} />
        </Router>
    );
  }
}

var font1 = new FontFaceObserver('Glyphicons Halflings');
var font2 = new FontFaceObserver('FontAwesome');

(function() {
    var el = document.getElementById('body-wrapper');
    Promise.all([font1.load(), font2.load()]).then(function (){
        render(<Provider store={store}>
            <App/>
        </Provider>, el);
    });
})();
