import React, { Component } from 'react';
import {Router, Link, IndexLink, hashHistory} from 'react-router';
var Bootstrap = require('react-bootstrap');
import {connect} from 'react-redux';
var moment = require('moment');
var Network = require('../network');

var SEVERITIES = {warning: { color: 'rgb(249, 196, 98)', icon: 'fa fa-exclamation-circle'}};
['notice', 'info', 'debug'].forEach(t => SEVERITIES[t] = { color: 'rgb(150, 230, 118)', icon: 'fa fa-info-circle'});
['emerg', 'alert', 'crit', 'err'].forEach(t => SEVERITIES[t] = { color: 'rgb(242, 140, 140)', icon: 'fa fa-times-circle '});

class Notification extends Component {
  constructor (props) {
    super(props);
    this.state = {
      show: false,
      newNotification: false,
      notifications: [],
      newNotifications: []
    }
    this.handleToggle = this.handleToggle.bind(this);
    this.readAll = this.readAll.bind(this);
  }

  componentDidMount() {
    var me=this;
    var ws;
    var host = window.location.host;
    if (host.indexOf(":") == 0) {
        host += ":80";
    }
    var protocol = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${protocol}://${host}/log`);
    ws.onmessage = evt => {
        var data = JSON.parse(evt.data);
       /* if (data.type === "update") {
            store.dispatch({ type: 'UPDATE_LOGS', log: data.message, host: data.message.host })
       } else if (data.type === "init") {
            logs = data.logs, hosts = data.hosts;
            store.dispatch({ type: 'INIT_LOGS', logs, hosts, selected_hosts: hosts })}*/
      if (data.type === "init_notifications") {
            var notifications_data=data.notifications;
            notifications_data.reverse();
            me.setState({notifications: notifications_data});
        } else if (data.type === "update_notifications") {
            var new_notification={message: data.message, timestamp: data.timestamp, severity: data.severity, host: data.host };
            var newNotifications_to_set=[new_notification, ...this.state.newNotifications];
            me.setState({newNotifications: newNotifications_to_set, newNotification: true});
        }
    };
    ws.onerror = evt => {
        ws.close();
        me.props.dispatch({ type: 'SHOW_ALERT', msg: "Socket error." });
    };
}
  handleToggle() {
    this.setState({ show: !this.state.show, newNotification: false });
  }

  componentWillUpdate(newProps) {
    if(newProps.newNotifications != this.props.newNotifications && newProps.newNotifications.length)
      this.setState({newNotification: true})
  }

  renderNotifications(n, className) {
    return n.map((n, i) => {
      const severity = SEVERITIES[n.severity];
      return (
        <div key={i} style={styles.row} className={className}>
          <i className={severity.icon} style={{fontSize: '30px', color: severity.color}} />
          <div style={styles.body}>
            <div style={styles.text}>{n.message}</div>
            <div style={styles.flexContainer}>
              <div style={styles.subText}>{moment(n.timestamp).fromNow()}</div>
              <div style={styles.subText}>{n.host}</div>
            </div>
          </div>
        </div>
      );
    });
  }

  readAll() {
    //this.props.dispatch({ type: 'READ_ALL_NOTIFICATIONS' });
    var newState_notifications = [...Object.assign([], this.state.newNotifications), ...this.state.notifications];
    var newState_newNotifications = [];
    this.setState({notifications: newState_notifications, newNotifications: newState_newNotifications});
  }

  render() {
    console.log('STATE: ', this.state);
    let classname = 'fa fa-bell fa-lg';
    if(this.state.newNotification) {
      classname += ' notification'
    }
    return (
      <Bootstrap.Nav pullRight>
        <span style={{position: 'relative'}}>
          <i
            className={classname}
            style={{color: '#fff', cursor: 'pointer'}}
            onClick={this.handleToggle}
          />
        </span>
        {this.state.show && [
            <div style={styles.overlay} onClick={this.handleToggle}></div>,
            <div style={styles.popup} id="notification-popup">
              <div style={styles.scroller}>
                {this.renderNotifications(this.state.newNotifications, 'new-notification')}
                {this.renderNotifications(this.state.notifications, '')}
              </div>
              <div style={styles.popupFooter}>
                <span className='clickable' onClick={this.readAll}>Read all notifications</span>
              </div>
            </div>]}
      </Bootstrap.Nav>
    )
  }
}

module.exports = connect(function(state) {
    return {auth: state.auth}
})(Notification);

const styles = {
  popup: {
    position: 'absolute',
    top: 55, //100%
    right: 65, //-15,
    backgroundColor: '#fff',
    width: 358,
    zIndex: 1000,
    border: '1px solid rgba(235,235,235,0.4)',
  },
  scroller: {
    overflowY: 'auto',
    maxHeight: 400,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: '100%',
    height: '100%',
    zIndex: 500
  },
  row: {
    borderBottom: '1px solid rgba(77,82,89,0.07)',
    padding: '10px',
    display: 'flex',
    alignItems: 'center'
  },
  body: {
    flexGrow: 1,
    paddingLeft: 8,
    minWidth: 0
  },
  text: {
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    textOverflow: 'ellipsis',
    lineHeight: '26px',
    fontSize: 13,
    height: '26px'
  },
  subText: {
    fontSize: 12,
    color: '#8b95a5'
  },
  flexContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    lineHeight: '26px'
  },
  icon: {
    fontSize: '20px'
  },
  popupFooter: {
    backgroundColor: '#f9fafb',
    padding: '8px 10px',
    color: '#8b95a5',
    height: 46,
    display: 'flex',
    alignItems: 'center'
  }
}