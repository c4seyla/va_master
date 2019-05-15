import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
var classNames = require('classnames');
import { connect } from 'react-redux';
var Network = require('../network');
import {Table, Tr, Td} from 'reactable';
import { getSpinner } from './util';

String.prototype.replaceAll = function (find, replace) {
    var str = this;
    return str.replace(new RegExp(find.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'g'), replace);
};

class UsersPermissions extends Component {
    constructor(props) {
        super(props);
        this.state = {
            loading: false,
            permUser: this.props.user,
            modal_open: false,
            selected_function_args: [],
            tableRows: []
        };
        this.handleAddPermission=this.handleAddPermission.bind(this);
        this.openModal=this.openModal.bind(this);
        this.closeModal=this.closeModal.bind(this);
        this.getArgumentsPerFuncPath=this.getArgumentsPerFuncPath.bind(this);
        this.getAllPermissions=this.getAllPermissions.bind(this);
        this.getCurrentUser=this.getCurrentUser.bind(this);
    }

    componentDidMount() {
        var me=this;
        this.getAllPermissions();
        var args=me.getArgumentsPerFuncPath(me.state.permUser.functions[0].func_path);
        this.setState({selected_function_args: args});
    }

    getAllPermissions(){
        var list_permissions=[];
        this.state.permUser.functions.forEach(function(func){
            if(func.hasOwnProperty('predefined_arguments')){
                Object.keys(func.predefined_arguments).forEach(function(arg){
                    if(Array.isArray(func.predefined_arguments[arg])){
                        list_permissions.push({func_path: func.func_path, request_parameter: arg, value: func.predefined_arguments[arg], type: 'list'});
                    }
                    else{
                        list_permissions.push({func_path: func.func_path, request_parameter: arg, value: func.predefined_arguments[arg], type: typeof func.predefined_arguments[arg]});
                    }
                });
            }
        });
        this.setState({tableRows: list_permissions});
    }

    openModal(){
        console.log('Modal opened !');
        this.setState({modal_open: true});
    }

    closeModal(){
        console.log('Modal closed !');
        this.setState({modal_open: false});
    }

    getCurrentUser (user_name) {
        var me = this;
        Network.get('/api/panels/users', this.props.auth.token)
        .done(function (data){
            var result = data.filter(user => user.user === user_name)[0];
            console.log(result);
            me.setState({permUser: result});
            me.getAllPermissions();
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    handleAddPermission(){
        var me=this;
        console.log('Add permissions button clicked !');
        var user=this.state.permUser.user;
        console.log('User: ', user);
        var select_element_value=document.getElementById('selectFunc').value;
        console.log('Selected_element_value: ', select_element_value);
        var args=this.getArgumentsPerFuncPath(select_element_value);
        console.log('Arguments', args);
        var object_data={};
        args.forEach(function(argg) {
            var permissions_rows=me.state.tableRows;
            var x=document.getElementById(argg.name);
            console.log(x, argg);
            if (!x) {}
            else if (x.value != '')        
            {
                if(argg.type === 'string'){
                        console.log(argg.name, ": ", x.value);
                        object_data[argg.name]=x.value;

                }

                if(argg.type === 'list'){
                        var lista=x.value.replaceAll(" ", "").split(',');
                        object_data[argg.name] = lista;
                        console.log('Lista', lista);
                }
            }
        });
        var data = {username: user, func_path: select_element_value, kwargs: object_data};

        var req1 = Network.post('/api/panels/add_args', me.props.auth.token, data).done(function(d) {
        }).fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
        $.when(req1).done(function(resp1) {
          // newArray.push({func_path: select_element_value, request_parameter: argg.name, value: x.value, type: 'string'});
           //me.setState({permUser: me.props.user});
           me.getCurrentUser(me.state.permUser.user);
        });

        me.setState({modal_open: false});
    }
    
    getArgumentsPerFuncPath(funcPath){

        var func = this.state.permUser.functions.filter(func => func.func_path === funcPath)[0];
        if(func != null){
            if(func.hasOwnProperty('arguments')){
                return func.arguments;
            }
            else{
                return [];
            }
        }
        else{
            return [];
        }
    }

    handleSelectChange(value){
        //console.log(value.target.value);
        var select_element_value=document.getElementById('selectFunc').value;
        var func_args=this.getArgumentsPerFuncPath(select_element_value);
        this.setState({selected_function_args: func_args});
    }

    render() {
        var me=this;
        var loading = this.state.loading;
        var functions_options=this.state.permUser.functions.map(function(func, index){
            return (<option value={func.func_path}>{func.func_path}</option>);
        });     
            var args=me.state.selected_function_args.map(function(arg, index){
                if(arg.hasOwnProperty('name')){
                    if(arg.type === 'string' || arg.type ==='list'){
                        return (
                        <div>
                            <Bootstrap.FormGroup>
                                <Bootstrap.ControlLabel><b>{arg.name} :</b></Bootstrap.ControlLabel>
                                <Bootstrap.FormControl id={arg.name} type='text' name={arg.name} placeholder={"Enter "+ arg.name} />
                            </Bootstrap.FormGroup>
                        </div>
                    );
                    }
                }
            });

            var args_types=me.state.selected_function_args.map(function(arg, index){
                if(arg.hasOwnProperty('name')){
                    if(arg.type === 'string' || arg.type === 'list'){
                        return (
                            <h3 style={{fontSize: '0.8em'}}> Type: {arg.type} <br/> <br/> <br/></h3>
                        );
                    }
                }
            });
        
        var permissions_rows=this.state.tableRows.map(function(row, index){
            return(<Tr key={index}>
                    <Td column="Function">{row.func_path}</Td>
                    <Td column="Request parameter">{row.request_parameter}</Td>
                    <Td column="Type">{row.type}</Td>
                    <Td column="Value">{row.value}</Td>
                </Tr>);
        });

        return (
                <div>
                    <Bootstrap.Modal show={this.state.modal_open} onHide={this.closeModal}>
                        <Bootstrap.Modal.Header closeButton>
                            <Bootstrap.Modal.Title>Add Permissions</Bootstrap.Modal.Title>
                        </Bootstrap.Modal.Header>
                        
                        <Bootstrap.Modal.Body>
                            <div className="left">
                                <Bootstrap.FormControl type='text' name="user" value={this.state.permUser.user} disabled={true} />
                                <Bootstrap.FormGroup>
                                    <Bootstrap.ControlLabel>Select function</Bootstrap.ControlLabel>
                                    <Bootstrap.FormControl id="selectFunc" componentClass="select" placeholder="Select function" onChange={this.handleSelectChange.bind(this)}>
                                        {functions_options}
                                    </Bootstrap.FormControl>
                                </Bootstrap.FormGroup>
                                <h4>Function arguments</h4>
                                {args}
                            </div>
                            <div className="right">
                                <br/><br/><br/><br/><br/><br/><br/><br/>
                                <div style={{marginTop: '10px'}}>
                                    {args_types}
                                </div>
                            </div>
                        </Bootstrap.Modal.Body>
                        
                        <Bootstrap.Modal.Footer>

                            <Bootstrap.Button onClick={this.closeModal}>Cancel</Bootstrap.Button>
                            <Bootstrap.Button onClick={this.handleAddPermission} bsStyle = "primary">Confirm</Bootstrap.Button>
                        </Bootstrap.Modal.Footer>
                        
                    </Bootstrap.Modal>
                    {loading && getSpinner()}
                    <div style={this.props.style} className="card">
                        <div className="card-body">
                            <h2>User Permissions</h2>
                            <Table className="table striped" columns={['Function', 'Request parameter', 'Type', 'Value']} itemsPerPage={10} pageButtonLimit={10} noDataText="No matching records found." sortable={true} filterable={['Function', 'Request parameter', 'Type', 'Value']} buttons={[{name: "Add permissions", onClick: this.openModal, icon: 'glyphicon glyphicon-plus'}]} btnClick={this.openModal} title="Permissions" filterClassName="form-control" filterPlaceholder="Filter">
                                {permissions_rows}
                            </Table>
                        </div>
                    </div>
                </div>);
}
}

module.exports = connect(state => {
    return { auth: state.auth, alert: state.alert, user: state.permissions.permUser};
})(UsersPermissions);