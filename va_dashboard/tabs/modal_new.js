import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
var Network = require('../network');
import {findDOMNode} from 'react-dom';
import Select from 'react-select-plus';
import {Table, Tr, Td} from 'reactable';
import { getSpinner } from './util';
import { hashHistory } from 'react-router';

class Modal extends Component {
    constructor (props) {
        super(props);
        var data = {
            type: -1,
            value: null,
            group: null
        };
        var type = this.props.type;
        if(type === 3){
            var user = this.props.user.user;
            console.log(user);
            data.value = user.functions;
            data.group = user.groups;
            data.user = user.user;
        }else if(type === 4){
            var group = this.props.selected_group;
            data.value = group.functions;
            data.group = group.func_name;
        }
        this.state = data;
        this.action = this.action.bind(this);
        this.typeChange = this.typeChange.bind(this);
        this.onChange = this.onChange.bind(this);
        this.onChangeGroup = this.onChangeGroup.bind(this);
    }

    action(e) {
        var elements = findDOMNode(this.refs.forma).elements;
        var data = {};
        for(let i=0; i<elements.length; i++){
            data[elements[i].name] = elements[i].value;
        }
        var me = this, url = "/api/panels/create_user_group", type = this.props.type;
        delete data[""]
        let funcs = Object.assign([], this.state.value);
        if(type == 1 || type == 3){
            url =(type == 1) ? "/api/panels/create_user_with_group" : "/api/panels/update_user";
            if(funcs.length > 0 && typeof funcs[0] === 'object'){
                for(let i=0; i<funcs.length; i++){
                    console.log('Funcs', funcs[i]);
                    funcs[i].group = funcs[i].func_name;
                }
            }
            data["functions"] = funcs;
            var groups = Object.assign([], this.state.group), g_arr = [];
            if(groups.length > 0){
                if(typeof groups[0] === 'object'){
                    for(let i=0; i<groups.length; i++){
                        g_arr.push(groups[i].value);
                    }
                }else{
                    g_arr = groups;
                }
            }
            data["groups"] = g_arr;
        }else{
            if(funcs.length > 0 && typeof funcs[0] === 'object'){
                for(let i=0; i<funcs.length; i++){
                    funcs[i].group = funcs[i].func_name;
                }
            }
            data["functions"] = funcs;
        }
        Network.post(url, this.props.auth.token, data).done(function(d) {
            type == 3 ? me.props.update(me.props.index, data) : me.props.add(data);
        }).fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    componentWillReceiveProps(nextProps){
        var me=this;
        console.log('Props ', nextProps);
       if(nextProps.user != undefined && nextProps.user != this.props.user){
            if(nextProps.user.functions.length > 0 && typeof nextProps.user.functions[0] == 'object'){
                var functions_values=nextProps.user.functions;
                var functions_paths_values=[];
                functions_values.forEach(function(element) {
                    functions_paths_values.push(element.func_path);
                });
                me.setState({value: functions_paths_values});
            }
            if(nextProps.user.functions.length > 0 && typeof nextProps.user.functions[0] == 'string'){
                me.setState({value: nextProps.user.functions})
            }
       }
        return true;
    }

    componentDidMount(){

    }

    typeChange (evt) {
        this.setState({type: evt.target.value});
    }

    onChange(value) {
        this.setState({ value: value });
    }

    onChangeGroup(value) {
        this.setState({ group: value });
    }

    render () {
        var type = this.props.type;
        if(type === -1)
            return <div></div>;
        var title, form, help_text, btn_text;
        if(type === 1){
            let selectGroup = null, selectFunc = null;
            title="Add user";
            btn_text = "Add user";
            help_text = "Fill the form to add new user";
            if(this.state.type === "user"){
                selectGroup = <Select name="groups" options={this.props.groups} multi={true} placeholder="Select groups" value={this.state.group} onChange={this.onChangeGroup} />
                selectFunc = <Select name="functions" options={this.props.funcs} multi={true} placeholder="Select functions" value={this.state.value} onChange={this.onChange} />
            }
            form = (
                <div>
                    <Bootstrap.FormControl type='text' name="user" placeholder="Username" />
                    <Bootstrap.FormControl type='password' name="password" placeholder="Password" />
                    <select className="form-control" value={this.state.type} name="user_type" onChange={this.typeChange}>
                        <option value="-1" disabled>Select user type</option>
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                    </select>
                    {selectGroup}
                    {selectFunc}
                </div>
            );
        }else if(type === 2){
            let title="Add group", btn_text = "Add group", help_text = "Fill the form to add new group";
            form = (
                <div>
                    <Bootstrap.FormControl type='text' name="group_name" placeholder="Group name" />
                    <Select name="functions" options={this.props.funcs} multi={true} placeholder="Select functions" value={this.state.value} onChange={this.onChange} />
                </div>
            );
        }else if(type === 3){
            title="Update user";
            btn_text = "Update user";
            help_text = "Fill the form to update the user";
            var functions_values=this.props.user.functions;

            var functions_paths_values=[];
            functions_values.forEach(function(element) {
                functions_paths_values.push(element.func_path);
            });


            form = (
                <div>
                    <Bootstrap.FormControl type='text' name="user" value={this.props.user.user} disabled={true} />
                    <Bootstrap.FormControl type='password' name="password" placeholder="Password" />
                    <Select name="groups" options={this.props.groups} multi={true} placeholder="Select groups" value={this.state.group} onChange={this.onChangeGroup} />
                    <Select name="functions" options={this.props.funcs} multi={true} placeholder="Select functions" value={this.state.value} onChange={this.onChange} />
                </div>
            );
        }else{
            title="Update group";
            btn_text = "Update group";
            help_text = "Fill the form to update the group";
            form = (
                <div>
                    <Bootstrap.FormControl type='text' name="group_name" value={this.state.group} />
                    <Select name="functions" options={this.props.funcs} multi={true} placeholder="Select functions" value={this.state.value} onChange={this.onChange} />
                </div>
            );
        }
        return (
            <Bootstrap.Modal show={this.props.isOpen} onHide={this.props.close}>
            <Bootstrap.Modal.Header closeButton>
                <Bootstrap.Modal.Title>{ title }</Bootstrap.Modal.Title>
            </Bootstrap.Modal.Header>

            <Bootstrap.Modal.Body>
                <div className="left">
                    <Bootstrap.Form ref="forma">
                        { form }
                    </Bootstrap.Form>
                </div>
                <div className="right">
                    <h3>{help_text}</h3>
                    <div></div>
                </div>
            </Bootstrap.Modal.Body>

            <Bootstrap.Modal.Footer>
                <Bootstrap.Button onClick={this.props.close}>Cancel</Bootstrap.Button>
                <Bootstrap.Button onClick={this.action} bsStyle = "primary">{btn_text}</Bootstrap.Button>
            </Bootstrap.Modal.Footer>

        </Bootstrap.Modal>
        );
    }
}

module.exports=Modal;