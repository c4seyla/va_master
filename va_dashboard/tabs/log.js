import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
import {connect} from 'react-redux';
var Network = require('../network');
import {DateRangePicker} from 'react-dates';
var moment = require('moment');
import {Table, Tr, Td} from 'reactable';
import Select from 'react-select-plus';

var SEV = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"];
var COLORS = ["#de4040", "#de4040", "#de4040", "#de4040", "#ffa726", "#777777", "#777777", "#777777"];

class Log extends Component {
    constructor (props) {
        super(props);
        let checked;
        switch (props.params.type) {
          case 'info':
            checked = ["notice", "info", "debug"]
            break;
          case 'warning':
            checked = ["warning"]
            break;
          case 'critical':
            checked = ["emerg", "alert", "crit", "err"]
            break;
          default:
            checked = Object.assign([], SEV);
        }
        this.state = {
            filterBy: "",
            checked,
            status: 1
        };
        this.statuses = ['start', 'stop'];
        this.filter = this.filter.bind(this);
        this.updateLogs = this.updateLogs.bind(this);
        this.changeObservableStatus = this.changeObservableStatus.bind(this);
        this.changeTable = this.changeTable.bind(this);
        this.changeStatus = this.changeStatus.bind(this);
        this.onChangeHost = this.onChangeHost.bind(this);
    }

    componentDidMount() {
      this.props.dispatch({type: 'GET_LOGS'});
    }

    componentWillUnmount() {
      this.changeObservableStatus('stop')
      this.props.dispatch({type: 'RESET_LOGS'});
    }

    filter(evt) {
        this.setState({filterBy: evt.target.value});
    }
    updateLogs(startDate, endDate){
        var msg = startDate ? {
            type: "get_messages",
            from_date: startDate,
            to_date: endDate
        } : {type: "get_messages"};
        this.props.dispatch({type: 'SEND_MESSAGE', msg});
    }
    changeObservableStatus(value){
        var msg = {
            type: "observer_status",
            status: value
        };
        this.props.dispatch({type: 'SEND_MESSAGE', msg});
    }
    changeTable(checked){
        this.setState({checked: checked});
    }
    changeStatus (e){
        var value = e.target.value;
        this.setState({status: 1 - value});
        this.changeObservableStatus(this.statuses[value]);
    }
    onChangeHost(value) {
        this.props.dispatch({ type: 'SELECT_HOST', selected_hosts: value })
    }
    render () {
        var counters = {};
        for(var i=0; i<SEV.length; i++)
            counters[SEV[i]] = 0;
        var hosts = this.props.selected_hosts.map(function(h){
            return h.value;
        });
        var logs = this.props.logs.filter(l => {
            if(SEV.indexOf(l.severity) > -1)
                counters[l.severity]++;
            if(this.state.checked.indexOf(l.severity) > -1 && hosts.indexOf(l.host) > -1)
                return true;
            return false;
        });
        logs.reverse();
        var status = this.state.status;
        return (
            <div id="log-page">
                <div>
                    <Bootstrap.Button onClick={this.changeStatus} value={status} style={{marginRight: '20px', textTransform: 'capitalize'}}>{this.statuses[status]} Live</Bootstrap.Button>
                    <DateRange updateLogs={this.updateLogs} state={status} />
                    <Select name="hosts" options={this.props.hosts} multi={true} placeholder="Filter hosts" value={this.props.selected_hosts} onChange={this.onChangeHost} style={{marginLeft: '20px', width: '500px'}} />
                </div>
                <div id='filter-log'>
                    <FilterBtns changeTable={this.changeTable} values={this.state.checked} counters={counters} />
                    <input type='text' placeholder='Filter' value={this.state.value} onChange={this.filter} className='form-control'/>
                </div>
                <LogTable logs={logs} filterBy={this.state.filterBy} newLogsNum={this.props.newLogs} />
            </div>
	);
    }
}

class DateRange extends Component {
    constructor (props) {
        super(props);
        this.state = {
            startDate: moment().subtract(1, 'days'),
            endDate: moment(),
            focusedInput: null
        }
        this.handleChange = this.handleChange.bind(this);
        this.focusChange = this.focusChange.bind(this);
    }

    handleChange(obj) {
        let { startDate, endDate } = obj;
        this.setState({startDate, endDate});
        this.props.updateLogs(startDate.format('YYYY-MM-DD'), endDate.format('YYYY-MM-DD'));
    }

    focusChange(focusedInput){
        this.setState({focusedInput: focusedInput});
    }

    render () {
        var state = this.props.state;
        return (
            <DateRangePicker
                displayFormat="YYYY-MM-DD"
                startDate={this.state.startDate}
                endDate={this.state.endDate}
                onDatesChange={this.handleChange}
                focusedInput={this.state.focusedInput}
                onFocusChange={this.focusChange}
                isOutsideRange={function(){return false}}
                disabled={!!state}
            />
        );
    }
}

class FilterBtns extends Component {
    constructor (props) {
        super(props);
        this.onChange = this.onChange.bind(this);
    }

	onChange(values) {
        this.props.changeTable(values);
	}

    render () {
        var me = this;
		var btns = SEV.map(function(val, i){
			return <Bootstrap.ToggleButton key={val} value={val}>{val} <span className="badge" style={{backgroundColor: COLORS[i]}}>{me.props.counters[val]}</span></Bootstrap.ToggleButton>;
		});
		return (
            <Bootstrap.ToggleButtonGroup type="checkbox" value={this.props.values} onChange={this.onChange}>
                {btns}
            </Bootstrap.ToggleButtonGroup>
		);
    }
}

class LogTable extends Component {
    constructor (props) {
        super(props);
        this.state = {
            selected_log: {}
        };
        this.rowSelected = this.rowSelected.bind(this);
    }

    rowSelected(evt) {
        var selected_row = this.props.logs.find(function(log){
            return log.timestamp === evt.currentTarget.id;
        });
        selected_row = Object.assign({}, selected_row);
        var msg = JSON.parse(selected_row['message']);
        selected_row['message'] = msg;
        selected_row['message']['method'] = msg['data']['method'];
        delete selected_row['message']['data'];
        this.setState({selected_log: selected_row});
    }

    render() {
        var logs = this.props.logs.map(function(log, index) {
            var msg = log.message, className = "row-log-" + log.severity;
            if(index < this.props.newLogsNum)
                className += ' new-log';
            /*try{
                var log_json = JSON.parse(msg);
                msg = msg.function;
            }catch (e){
                console.log("JSON error ", index.toString());
                console.log(log.message);
            }*/
            //if(this.state.selected_log.timestamp === log.timestamp)
            //    className = "info";
            return (
                <Tr key={log.timestamp} id={log.timestamp} className={className} onClick={this.rowSelected}>
                    <Td column="Timestamp" style={{minWidth: '100px'}}>{log.timestamp.substring(0,19).split('T').join(' ')}</Td>
                    <Td column="Host">{log.host}</Td>
                    <Td column="Severity">{log.severity}</Td>
                    <Td column="Message" className="ellipsized-text2">{msg}</Td>
                </Tr>
            );
        }.bind(this));
        var selected_log = [];
        if("message" in this.state.selected_log){
            var msg = this.state.selected_log.message;
            //msg['method'] = JSON.parse(msg['data'])[;
            for(var key in msg){
                var div = (<div key={key}><b>{key}:</b> {msg[key].toString()}</div>);
                selected_log.push(div);
            }
        }
        var columns = ["Timestamp", "Host", "Severity", "Message"];
        return ( <div>
            <Table className="table striped card" columns={columns} itemsPerPage={10} pageButtonLimit={10} noDataText="No matching records found." sortable={true} filterable={columns} filterBy={this.props.filterBy} hideFilterInput>
                {logs}
            </Table>
        </div> );
    }
}


module.exports = connect(function(state){
    return {auth: state.auth, alert: state.alert, ...state.logs, ...state.hosts};
})(Log);
