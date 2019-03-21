import React, { Component } from 'react';
import { Router, Link, IndexLink, hashHistory } from 'react-router';
var Bootstrap = require('react-bootstrap');
var classNames = require('classnames');
import { connect } from 'react-redux';
var Network = require('../network');
import {Table, Tr, Td} from 'reactable';
import { getSpinner } from './util';
import ReactJson from 'react-json-view'

String.prototype.replaceAll = function (find, replace) {
    var str = this;
    return str.replace(new RegExp(find.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'g'), replace);
};

class API extends Component {
    constructor(props) {
        super(props);
        this.state = {
            funcs: [],
            groups: [],
            group_opt: [],
            loading: true,
            funcDetails: {}
        };
        this.getCurrentFuncs = this.getCurrentFuncs.bind(this);
        this.handleSelect= this.handleSelect.bind(this);
        this.showFunctionDetails=this.showFunctionDetails.bind(this);
        this.checkOutput=this.checkOutput.bind(this);
    }

    getCurrentFuncs() {
        var me = this;
        var n1 = Network.get('/api/panels/get_all_functions', this.props.auth.token)
            .fail(function(msg) {
                me.props.dispatch({ type: 'SHOW_ALERT', msg: msg });
            });

        var n2 = Network.get('/api/panels/get_all_function_groups', this.props.auth.token)
            .fail(function(msg) {
                me.props.dispatch({ type: 'SHOW_ALERT', msg: msg });
            });

        $.when(n1, n2).done(function(resp1, resp2) {
            console.log('Response 1', resp1);
            console.log('Response 2', resp2);
            var groups = resp2.map(function(group) {
                return { value: group.func_name, label: group.func_name };
            });
            me.setState({ funcs: resp1, groups: resp2, group_opt: groups, loading: false });
            var acc = document.getElementsByClassName("accordion");

        for (var i = 0; i < acc.length; i++) {
            acc[i].addEventListener("click", function() {
                /* Toggle between adding and removing the "active" class,
                to highlight the button that controls the panel */
                this.classList.toggle("active");

                /* Toggle between hiding and showing the active panel */
                var panel = this.nextElementSibling;
                if (panel.style.display === "block") {
                    panel.style.display = "none";
                } else {
                    panel.style.display = "block";
                }
            });
        }
        });
    }

    componentDidMount() {
        this.getCurrentFuncs();
    }

    handleSelect(option){
        this.setState({funcDetails: option});
    }

    isEmpty(obj) {
        for(var key in obj) {
            if(obj.hasOwnProperty(key))
                return false;
        }   
        return true;
    }

    checkOutput(output, type){
        if(typeof output == 'string'){
            if(type=='output'){
                return(<p style={{textAlign: 'justify'}}><b>Output:</b> {output}</p>);
            }
            else{
                return(<p style={{textAlign: 'justify'}}><b>Example data:</b> {output}</p>);
            }
        }
        else{
            if(this.isEmpty(output) == false){
                 if(type=='output'){
                    return(<div><b>Output: </b><ReactJson name={null} src={output} enableEdit={false} enableDelete={false} enableAdd={false} enableClipboard={false} displayDataTypes={true} displayObjectSize={false}/></div>);
                }
                else{
                    return(<div><b>Example data: </b><ReactJson name={null} src={output} enableEdit={false} enableDelete={false} enableAdd={false} enableClipboard={false} displayDataTypes={true} displayObjectSize={false}/></div>);
                }
            }
        }
    }

    showFunctionDetails(){
        var me=this;
        console.log(me.state.funcDetails);
        if(this.isEmpty(this.state.funcDetails) == false){
            if(this.state.funcDetails.documentation.hasOwnProperty('arguments')){

                var rows = this.state.funcDetails.documentation.arguments.map(function(funcarg, index) {
            return (
                <Tr key={funcarg.name}>
                    <Td column="Name">{funcarg.name}</Td>
                    <Td column="Type">{funcarg.type}</Td>
                    <Td column="Description">{funcarg.description}</Td>
                    <Td column="Required">{funcarg.required}</Td>
                    <Td column="Default">{funcarg.default}</Td>
                </Tr>
            );
        }, this);
        
            return (<div>

                    <h2 style={{fontWeigth: 'bold'}}>{this.state.funcDetails.label}</h2>
                    <br/>
                    <p style={{textAlign: 'justify'}}><b>Description:</b> {this.state.funcDetails.documentation.description}</p>
                    <p><b>URL:</b><pre><code>{this.state.funcDetails.method.toUpperCase()}&nbsp;&nbsp;{this.state.funcDetails.example_url}</code></pre></p>
                    <p><b>CURL Example:</b><pre><code>{this.state.funcDetails.example_cli.replaceAll('\\"','"')}</code></pre></p>
                    {this.checkOutput(this.state.funcDetails.example_data, 'data')}
                    <Table className="table striped" columns={['Name', 'Type', 'Description', 'Required', 'Default']} itemsPerPage={10} pageButtonLimit={10} noDataText="No matching records found." sortable={true} filterable={['Name', 'Type', 'Description', 'Required', 'Default']}  title="Request parameters" filterClassName="form-control" filterPlaceholder="Filter">
                        {rows}
                    </Table>
                    {this.checkOutput(this.state.funcDetails.documentation.output, 'output')}
                    </div>);
            }
            else{
                return (<div>

                    <h2 style={{fontWeigth: 'bold'}}>{this.state.funcDetails.label}</h2>
                    <br/>
                    <p style={{textAlign: 'justify'}}><b>Description:</b> {this.state.funcDetails.documentation.description}</p>
                    <p><b>URL:</b><pre><code>{this.state.funcDetails.method.toUpperCase()}&nbsp;&nbsp;{this.state.funcDetails.example_url}</code></pre></p>
                    <p><b>CURL Example:</b><pre><code>{this.state.funcDetails.example_cli.replaceAll('\\"','"')}</code></pre></p>
                    {this.checkOutput(this.state.funcDetails.example_data, 'output')}
                    </div>);
            }
        }
    }

    render() {
        var me=this;
        var loading = this.state.loading;
        var funcs=this.state.funcs.map(function(func, index){
            if(func.options.length == 0){
                return (<Bootstrap.Button bsSize="large" style={{textAlign: 'left'}}>{func.label}</Bootstrap.Button>);
            }
            else{

                var options=func.options.map(function(option, index){
                    return (<Bootstrap.MenuItem eventKey={index} onClick={() => me.handleSelect(option)} style={{textAlign: 'left'}}>{option.label}</Bootstrap.MenuItem>);
                });
                
                return( <Bootstrap.DropdownButton bsSize="large" title={func.label} id="dropdown-size-large" style={{textAlign: 'left'}}>
                            {options}
                        </Bootstrap.DropdownButton>);
            }
        });

        var funcs_accordion=this.state.funcs.map(function(func, index){
            if(func.options.length == 0){
                return (<div><button className="accordion">{func.label}</button>
                        </div>);
            }
            else{

                var options=func.options.map(function(option, index){
                    return(
                        <a role='button' className="btn btn-secondary btn-lg btn-block" onClick={() => me.handleSelect(option)} style={{backgroundColor: '#f5f5f5', color: 'black', textAlign: 'left', borderTop: '1px solid #ccc'}}>
                            {option.label}
                        </a>)
                });
                
                return(<div><button className="accordion">{func.label}&nbsp;&nbsp;<i className="fa fa-caret-down"></i>
</button>
<div className="panel" style={{border: '1px solid #ccc'}}>
    {options}
</div></div>);
            }
        });
        return (
                <div>
                    {loading && getSpinner()}
                    <div style={this.props.style} className="card">
                        <div className="card-body">
                            <h2>API Documentation</h2>
                            <br/>
                            {/*<iframe src="http://127.0.0.1:1880" width="100%" height="1200px"></iframe>*/}
                            <div className="col-container">
                            <div className="sidebar-width">
                                <Bootstrap.ButtonGroup vertical block>
                                {funcs_accordion}
                                </Bootstrap.ButtonGroup>
                            </div>

                            <div className="details-api">
                               {this.showFunctionDetails()}
                            </div>
                            </div>
                        </div>

                        
                    </div>
                </div>);
}
}

module.exports = connect(state => {
    return { auth: state.auth, alert: state.alert };
})(API);