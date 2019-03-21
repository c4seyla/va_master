import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
import {connect} from 'react-redux';
var Network = require('../network');
import {findDOMNode} from 'react-dom';
import Select from 'react-select-plus';
import {Table, Tr, Td} from 'reactable';
import { getSpinner } from './util';
import { hashHistory } from 'react-router';
var Modal=require('./modal_new');

class UserGroupPanel extends Component {
    constructor (props) {
        super(props);
        this.state = {
            funcs: [],
            groups: [],
            group_opt: [],
            loading: true
        };
        this.getCurrentFuncs = this.getCurrentFuncs.bind(this);
    }

    getCurrentFuncs () {
        var me = this;
        var n1 = Network.get('/api/panels/get_all_functions', this.props.auth.token)
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
        var n2 = Network.get('/api/panels/get_all_function_groups', this.props.auth.token)
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
        $.when( n1, n2 ).done(function ( resp1, resp2 ) {
            var groups = resp2.map(function(group) {
                return {value: group.func_name, label: group.func_name};
            });
            me.setState({funcs: resp1, groups: resp2, group_opt: groups, loading: false});
        }); 
    }

    componentDidMount () {
        this.getCurrentFuncs();
    }

    render () {
        var UserRedux = connect(function(state){
            return {auth: state.auth, alert: state.alert};
        })(Users);

        var loading = this.state.loading;
        const blockStyle = {
            visibility: loading ? "hidden": "visible"
        };

        return (
            <div className="app-containter">
                {loading && getSpinner()}
                <Users funcs = {this.state.funcs} groups = {this.state.group_opt} style={blockStyle} auth={this.props.auth} dispatch={this.props.dispatch}/>
            </div>
        )
    }
}


class Users extends Component {
    constructor (props) {
        super(props);
        this.state = {
            users: [],
            modal_open: false,
            update: false,
            selected_user: {}
        };
        this.getCurrentUsers = this.getCurrentUsers.bind(this);
        this.openModal = this.openModal.bind(this);
        this.addUser = this.addUser.bind(this);
        this.updateUser = this.updateUser.bind(this);
        this.closeModal = this.closeModal.bind(this);
        this.btn_clicked = this.btn_clicked.bind(this);
    }

    getCurrentUsers () {
        var me = this;
        Network.get('/api/panels/users', this.props.auth.token)
        .done(function (data){
            console.log('Get users');
            me.setState({users: data});
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    componentDidMount () {
       this.getCurrentUsers();
    }

    openModal() {
        this.setState({modal_open: true, update: false});
    }
    getSelectedUser(){
        return this.state.selected_user;
    }
    addUser(data) {
        var users = Object.assign([], this.state.users);
        data.functions = data.functions.map(function(f){
            return f.value;
        });
        users.push(data);
        this.setState({modal_open: false, users: users});
    }

    updateUser(index, data) {
        var users = Object.assign([], this.state.users);
        if(data.functions.length > 0 && typeof data.functions[0] === 'object'){
            data.functions = data.functions.map(function(f){
                console.log('f',f);
                return f.value;
            });
        }
        users[index] = data;
        console.log('Users', users);
        this.setState({modal_open: false, users: users});
    }

    closeModal() {
        this.setState({modal_open: false});
    }

    btn_clicked(index, evtKey){
        var tt=this;
        var users = Object.assign([], this.state.users);
        var user = users[index];
        if(evtKey === "remove"){
            var data = {user: user.user}, me = this;
            Network.post('/api/panels/delete_user', this.props.auth.token, data).done(function(d) {
                users.splice(index, 1);
                me.setState({users: users});
            }).fail(function (msg) {
                me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
            });
        }else if(evtKey === "update"){
            this.setState({modal_open: true, update: index, selected_user: user});
        }else{
            console.log('Permissions per user', user);
            tt.props.dispatch({type: 'USER_PERMISSIONS', permUser: user});
            hashHistory.push('/users_permissions');
        }
    }

    render() {
        var me=this;
        var user_rows = this.state.users.map(function(user, index) {
            var functions_array=user.functions;
            var funcs=[];
            if(functions_array.length >0 && typeof functions_array[0]=== 'object'){

                var functions_path_array=[];
                functions_array.forEach(function(element) {
                    functions_path_array.push(element.func_path);
                });
                var groups = user.groups.join(', ');
                //var funcs = user.functions.join(', ');
                funcs=functions_path_array.join(', ');
            }
            else{
                funcs=functions_array.join(', ');
            }
            return (
                <Tr key={user.user}>
                    <Td column="Username">{user.user}</Td>
                    <Td column="Groups">{groups}</Td>
                    <Td column="Functions">{funcs}</Td>
                    <Td column="Actions">
                        <Bootstrap.DropdownButton bsStyle='primary' title="Choose" onSelect = {this.btn_clicked.bind(null, index)}>
                            <Bootstrap.MenuItem eventKey="remove">Remove</Bootstrap.MenuItem>
                            <Bootstrap.MenuItem eventKey="update">Update</Bootstrap.MenuItem>
                            <Bootstrap.MenuItem eventKey="permissions">Permissions</Bootstrap.MenuItem>
                        </Bootstrap.DropdownButton>
                    </Td>
                </Tr>
            );
        }, this);
        var modal;
        if(typeof this.state.update === "number"){
            modal = <Modal user={me.state.selected_user} type = {3} isOpen = {this.state.modal_open} update = {this.updateUser} index = {this.state.update} close = {this.closeModal} funcs = {this.props.funcs} groups = {this.props.groups} auth={this.props.auth}/>
        }else{
            modal = <Modal type = {1} isOpen = {this.state.modal_open} add = {this.addUser} close = {this.closeModal} funcs = {this.props.funcs} groups = {this.props.groups} auth={this.props.auth} dispatch={this.props.dispatch} />
        }

        return ( 
            <div style={this.props.style} className="card">
                {modal}
                <div className="card-body">
                    <Table className="table striped" columns={['Username', 'Groups', 'Functions', 'Actions']} itemsPerPage={10} pageButtonLimit={10} noDataText="No matching records found." sortable={true} filterable={['Username', 'Groups', 'Functions', 'Actions']} buttons={[{name: "Add user", onClick: this.openModal, icon: 'glyphicon glyphicon-plus'}]} btnClick={this.openModal} title="Dashboard Users" filterClassName="form-control" filterPlaceholder="Filter">
                        {user_rows}
                    </Table>
                </div>
            </div> 
        );
    }
}

class Groups extends Component {
    constructor (props) {
        super(props);
        this.state = {
            groups: Object.assign([], this.props.groups),
            modal_open: false,
            update: false,
            selected_group: {}
        };
        this.openModal = this.openModal.bind(this);
        this.addGroup = this.addGroup.bind(this);
        this.updateGroup = this.updateGroup.bind(this);
        this.closeModal = this.closeModal.bind(this);
        this.btn_clicked = this.btn_clicked.bind(this);
    }

    /*getCurrentGroups: function () {
        var me = this;
        Network.get('/api/panels/get_all_function_groups', this.props.auth.token)
        .done(function(data){
            me.setState({groups: data});
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    },*/

    openModal() {
        this.setState({modal_open: true, update: false});
    }

    addGroup(data) {
        var groups = Object.assign([], this.state.group);
        data.groups = data.groups.map(function(g){
            return g.value;
        });
        groups.push(data);
        this.setState({modal_open: false, groups: groups});
    }

    updateGroup(index, data) {
        var groups = Object.assign([], this.state.groups);
        if(data.functions.length > 0 && typeof data.functions[0] === 'object'){
            data.functions = data.functions.map(function(f){
                return f.value;
            });
        }
        groups[index] = data;
        this.setState({modal_open: false, groups: groups});
    }

    closeModal() {
        this.setState({modal_open: false});
    }

    btn_clicked(index, evtKey){
        var groups = Object.assign([], this.state.groups);
        var group = groups[index];
        if(evtKey === "remove"){
            var data = {group_name: group.func_name}, me = this;
            Network.post('/api/panels/delete_group', this.props.auth.token, data).done(function(d) {
                groups.splice(index, 1);
                me.setState({groups: groups});
            }).fail(function (msg) {
                me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
            });
        }else{
            this.setState({modal_open: true, update: index, selected_group: group});
        }
    }

    render () {
        var group_rows = this.state.groups.map(function(group, index) {
            var funcs = group.functions.join(', ');
            return (
                <Tr key={group.func_name}>
                    <Td column="Group name">{group.func_name}</Td>
                    <Td column="Functions">{funcs}</Td>
                    <Td column="Actions">
                        <Bootstrap.DropdownButton bsStyle='primary' title="Choose" onSelect = {this.btn_clicked.bind(null, index)}>
                            <Bootstrap.MenuItem eventKey="remove">Remove</Bootstrap.MenuItem>
                            <Bootstrap.MenuItem eventKey="update">Update</Bootstrap.MenuItem>
                        </Bootstrap.DropdownButton>
                    </Td>
                </Tr>
            );
        }, this);


        var modal;
        if(typeof this.state.update === "number"){
            modal = <Modal type = {4} isOpen = {this.state.modal_open} update = {this.updateGroup} index = {this.state.update} selected_group = {this.state.selected_group} close = {this.closeModal} funcs = {this.props.funcs} />
        }else{
            modal = <Modal type = {2} isOpen = {this.state.modal_open} add = {this.addGroup} close = {this.closeModal} funcs = {this.props.funcs} />
        }

        return (
            <div style={this.props.style} className="card">
                {modal}
                <div className="card-body">
                    <Table className="table striped" columns={['Group name', 'Functions', 'Actions']} itemsPerPage={10} pageButtonLimit={10} noDataText="No matching records found." sortable={true} filterable={['Group name', 'Functions', 'Actions']} buttons={[{name: "Add group", onClick: this.openModal, icon: 'glyphicon glyphicon-plus'}]} btnClick={this.openModal} title="Dashboard Groups" filterClassName="form-control" filterPlaceholder="Filter">
                        {group_rows}
                    </Table>
                </div>
            </div>
        );
    }
}

/*class Modal extends Component {
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
       if(nextProps.user != undefined){
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
                    <Select name="groups" options={this.props.groups} multi={true} placeholder="Select groups" value={this.props.user.groups} onChange={this.onChangeGroup} />
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
}*/

module.exports = {
    Panel: connect(state => {
        return {auth: state.auth, alert: state.alert};
    })(UserGroupPanel),
    Group: connect(state => {
        return {auth: state.auth, alert: state.alert};
    })(Groups)
};
