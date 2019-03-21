import React, { Component } from 'react';
var Bootstrap = require('react-bootstrap');
var classNames = require('classnames');
import { connect } from 'react-redux';
var Network = require('../network');
import { getSpinner } from './util';
import ReactJson from 'react-json-view';
import vis from '../static/vis';

class Integrations extends Component {
    constructor(props) {
        super(props);
        this.state = {
            loading: true,
            showModal: false,
            stepIndex: 1,
            apps:[],
            functions: [],
            eventsPerApp: [],
            actionsPerApp: [],
            selectedDonorApp: '',
            selectedReceiverApp: '',
            selectedEvent: {},
            selectedAction: {},
            integrations: []
        };
        this.openTriggerModal=this.openTriggerModal.bind(this);
        this.closeModal=this.closeModal.bind(this);
        this.nextStep=this.nextStep.bind(this);
        this.addTrigger=this.addTrigger.bind(this);
        this.showModalButtons=this.showModalButtons.bind(this);
        this.getApps=this.getApps.bind(this);
        this.getFunctions=this.getFunctions.bind(this);
        this.getEventsPerApp=this.getEventsPerApp.bind(this);
        this.getAppPerName=this.getAppPerName.bind(this);
        this.reloadModal=this.reloadModal.bind(this);
        this.showEventsSelect=this.showEventsSelect.bind(this);
        this.showActionsSelect=this.showActionsSelect.bind(this);
        this.getFunctionPerName=this.getFunctionPerName.bind(this);
        this.showArgumentMapSelect=this.showArgumentMapSelect.bind(this);
        this.formArgumentMap=this.formArgumentMap.bind(this);
        this.formTriggerJSON=this.formTriggerJSON.bind(this);
        this.getTriggers=this.getTriggers.bind(this);
        this.formGraph=this.formGraph.bind(this);
    }

    componentDidMount() {
        var me=this;
        me.setState({loading: false});
        this.getApps();
        this.getTriggers();
        //var nodes_edges_data=this.formGraph();
        // create an array with nodes
      // var nodes = new vis.DataSet([
      //   {id: 1, label: 'va-email-app'},
      //   {id: 2, label: 'event: va_email.add_user_recipient'},
      //   {id: 3, label: 'event: va_email.add_user'},
      //   {id: 4, label: 'condition: If recipient is valid and in cloudshare'},
      //   {id: 5, label: 'condition: If recipient is valid'},
      //   {id: 6, label: 'condition: If user in ldap'},
      //   {id: 7, label: 'action: add_contact_to_calendar'},
      //   {id: 8, label: 'action: add_contact_vcard'},
      //   {id: 9, label: 'action: add_uesr_to_cloudshare'},
      //   {id: 10, label: 'va-cloudshare-app'},
      // ]);

      //var nodes=new vis.DataSet(nodes_edges_data.nodes);
      // create an array with edges
      // var edges = new vis.DataSet([
      //   {from: 1, to: 2},
      //   {from: 1, to: 3},

      //   {from: 2, to: 4},
      //   {from: 2, to: 5},
      //   {from: 3, to: 6},

      //   {from: 4, to: 7},
      //   {from: 5, to: 8},
      //   {from: 6, to: 9},

      //   {from: 7, to: 10},
      //   {from: 8, to: 10},
      //   {from: 9, to: 10},
      // ]);

    //   var edges=new vis.DataSet(nodes_edges_data.edges);
    //   // create a network
    //   var container = document.getElementById('mynetwork');
    //   var data = {
    //     nodes: nodes,
    //     edges: edges
    //   };
      
    // var options = {
    //   manipulation: false,
    //   layout: {
    //     hierarchical: {
    //       direction: "LR",
    //       sortMethod: "directed",
    //       enabled: true,
    //       nodeSpacing: 100,
    //       levelSeparation: 400
    //     }
    //   },
    //   nodes: {
    //     shape: 'box',
    //     borderWidth: 4,
    //     color: '#006eab',
    //     font:{
    //         color: 'white',
    //         size: 20,
    //         bold: true
    //     }
    //   }
    // };
    //   var network = new vis.Network(container, data, options);
    }


    reloadModal(){
        var me=this;
        this.getEventsPerApp(this.state.apps[0].name);
        this.getActionsPerApp(this.state.apps[0].name);
        if(this.state.apps.length>0){
            me.setState({selectedDonorApp: me.state.apps[0].name , selectedReceiverApp: me.state.apps[0].name});
            me.getEventsPerApp(me.state.apps[0].name);
            me.getActionsPerApp(me.state.apps[0].name);
        }
    }

    getTriggers(){
        // var integrations=[{
        //                     "donor_app": "va-email",
        //                     "receiver_app": "va-cloudshare",
        //                     "events": [{
        //                             "event_name": "va_email.add_user_recipient",
        //                             "conditions": [{
        //                                 "func_name": "check_user_legit"
        //                             }, {
        //                                 "func_name": "check_user_in_ldap"
        //                             }],
        //                             "actions": [{
        //                                 "func_name": "add_contact_vcard"
        //                             }]
        //                         },
        //                         {
        //                             "event_name": "va_email.add_user",
        //                             "conditions": [{
        //                                 "func_name": "check_user_legit"
        //                             }, {
        //                                 "func_name": "check_user_not_in_cloudshare"
        //                             }],
        //                             "actions": [{
        //                                 "func_name": "add_cloudshare_user"
        //                             }, 
        //                             {
        //                                 "func_name": "add_contact_vcard"
        //                             }]
        //                         }
        //                     ]
        //                 },
        //                 {
        //                     "donor_app": "email",
        //                     "receiver_app": "cloudshare",
        //                     "events": [{
        //                             "event_name": "va_email.add_user_recipient",
        //                             "conditions": [{
        //                                 "func_name": "check_user_legit"
        //                             }, {
        //                                 "func_name": "check_user_in_ldap"
        //                             }],
        //                             "actions": [{
        //                                 "func_name": "add_contact_vcard"
        //                             }]
        //                         },
        //                         {
        //                             "event_name": "va_email.add_user",
        //                             "conditions": [{
        //                                 "func_name": "check_user_legit"
        //                             }, {
        //                                 "func_name": "check_user_not_in_cloudshare"
        //                             }],
        //                             "actions": [{
        //                                 "func_name": "add_cloudshare_user"
        //                             }, 
        //                             {
        //                                 "func_name": "add_contact_vcard"
        //                             }]
        //                         }
        //                     ]
        //                 }
        //                 ];

        var me=this;
        var integrations=[];
        Network.get('api/integrations', me.props.auth.token)
        .done(function (data){
            integrations=data;
            me.formGraph(integrations);

        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    formGraph(integrations){
        var ctr=0;
        var nodes=[];
        var edges=[];
        integrations.forEach(function(integration){
            var receiver_app=integration.receiver_app;
            var donor_app=integration.donor_app;

            var donor_app_node={id: ctr++, label: donor_app};
            var receiver_app_node={id: ctr++, label: receiver_app};
            nodes.push(donor_app_node);
            nodes.push(receiver_app_node);

            var events=integration.triggers;
            events.forEach(function(event){
                var event_node={id: ctr++, label: event.event_name};
                var event_edge={from: donor_app_node.id, to: event_node.id};
                nodes.push(event_node);
                edges.push(event_edge);
                var last_node={};
                if(event.conditions.length == 0){
                    last_node=event_node;
                }
                else{
                    var condition_val='';
                    event.conditions.forEach(function(condition){
                        condition_val=condition_val+condition.func_name+" AND ";
                    });
                    var condition_node={id: ctr++, label: condition_val};
                    var condition_edge={from: event_node.id, to: condition_node.id};
                    nodes.push(condition_node);
                    edges.push(condition_edge);
                    last_node=condition_node;
                }
                var actions=event.actions;
                
                actions.forEach(function(action){
                    var action_node={id: ctr++, label: action.func_name};
                    var action_edge={from: last_node.id, to: action_node.id};
                    var receiver_edge={from: action_node.id, to: receiver_app_node.id}
                    nodes.push(action_node);
                    edges.push(action_edge);
                    edges.push(receiver_edge);
                });
                
            });
        });
        var nodes=new vis.DataSet(nodes);
        var edges=new vis.DataSet(edges);
        // create a network
        var container = document.getElementById('mynetwork');
        var data = {
            nodes: nodes,
            edges: edges
        };
          
        var options = {
          manipulation: false,
          layout: {
            hierarchical: {
              direction: "LR",
              sortMethod: "directed",
              enabled: true,
              nodeSpacing: 100,
              levelSeparation: 400
            }
          },
          nodes: {
            shape: 'box',
            borderWidth: 4,
            color: '#006eab',
            font:{
                color: 'white',
                size: 20,
                bold: true
            }
          }
        };
        var network = new vis.Network(container, data, options);
    }
    
    openTriggerModal(){
        this.setState({showModal: true});
    }

    getAppPerName(appName){
        return this.state.apps.filter(app => app.name == appName)[0];
    }

    getFunctionPerName(funcName){
        return this.state.functions.filter(func => func.func_name == funcName)[0];
    }

    getApps(){
        var me=this;
        console.log('Calling get apps');
        Network.get('/api/states', this.props.auth.token)
        .done(function (data){
            var result = data;
            var app_list=[];
            result.forEach(function(appObject){
                app_list.push(appObject);
            });
            if(app_list.length > 0){
                me.setState({selectedDonorApp: app_list[0].name, selectedReceiverApp: app_list[0].name});
            }
            me.setState({apps: app_list});
            me.getFunctions();
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    getFunctions(){
        var me=this;
        Network.get('/api/panels/get_functions', this.props.auth.token)
        .done(function (data){
            var result = data;
            var functions_list=[];
            result.forEach(function(functionObject){
                functions_list.push(functionObject);
            });
            me.setState({functions: functions_list});
            me.getEventsPerApp(me.state.apps[0].name);
            me.getActionsPerApp(me.state.apps[0].name);
            me.setState({loading: false});
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    getEventsPerApp(appName){
        var app = this.getAppPerName(appName);
        var me=this;
        var event_list=[];
        var result=me.state.functions;
        result.forEach(function(functionObject){
            if(functionObject.event == true && functionObject.func_group == app.module){
                event_list.push(functionObject.func_name);
            }
        });
        
        if(event_list.length > 0){
            //document.getElementById("selectEvent").disabled = false;
            me.setState({selectedEvent: me.getFunctionPerName(event_list[0])});
        }
        else{
            me.setState({selectedEvent: {}});
        }
        me.setState({eventsPerApp: event_list});
    }

    getActionsPerApp(appName){
        var app = this.getAppPerName(appName);
        var me=this;
        var action_list=[];
        var result=me.state.functions;
        result.forEach(function(functionObject){
            if(functionObject.func_group == app.module){
                action_list.push(functionObject.func_name);
            }
        });
        
        if(action_list.length > 0){
            //document.getElementById("selectAction").disabled = false;
            me.setState({selectedAction: me.getFunctionPerName(action_list[0])});
        }
        else{
            me.setState({selectedAction: {}});
        }
        me.setState({actionsPerApp: action_list});
    }

    closeModal(){
        this.setState({showModal: false, stepIndex: 1});
        this.reloadModal();
    }

    nextStep(){
        if(this.state.stepIndex < 3){
            this.setState({stepIndex: this.state.stepIndex+1});
        }
    }

    addTrigger(){
        var me=this;
        console.log('ADD Trigger Button clicked');
        var new_trigger=this.formTriggerJSON();
        console.log('New trigger: ', new_trigger);
        Network.post('/api/integrations/add_trigger', this.props.auth.token, new_trigger)
        .done(function (data){
            me.props.dispatch({type: 'SHOW_ALERT', msg: 'Succesfully added trigger'});
        })
        .fail(function (msg) {
            me.props.dispatch({type: 'SHOW_ALERT', msg: msg});
        });
    }

    handleSelectDonorAppChange(){
        var select_element_value=document.getElementById('selectDonorApp').value;
        this.setState({selectedDonorApp: select_element_value});
        this.getEventsPerApp(select_element_value);
    }

    handleSelectEventChange(){
        var select_element_value=document.getElementById('selectEvent').value;
        var event = this.getFunctionPerName(select_element_value);      
        this.setState({selectedEvent: event});
    }

    handleSelectReceiverAppChange(){
        var select_element_value=document.getElementById('selectReceiverApp').value;
        this.setState({selectedReceiverApp: select_element_value});
        this.getActionsPerApp(select_element_value);
    }

    handleSelectActionChange(){
        var select_element_value=document.getElementById('selectAction').value;
        var act = this.getFunctionPerName(select_element_value); 
        this.setState({selectedAction: act});
    }

    showEventsSelect(){
        var event_options=this.state.eventsPerApp.map(function(event, index){
            return (<option value={event}>{event}</option>);
        });

        if(this.state.eventsPerApp.length==0){
            return(
            <Bootstrap.FormGroup disabled>
                <Bootstrap.ControlLabel disabled>Select event</Bootstrap.ControlLabel>
                <Bootstrap.FormControl id="selectEvent" componentClass="select" placeholder="Select event" onChange={this.handleSelectEventChange.bind(this)} disabled>
                    {event_options}
                </Bootstrap.FormControl>
            </Bootstrap.FormGroup>);
        }
        else{
            return(
            <Bootstrap.FormGroup>
                <Bootstrap.ControlLabel>Select event</Bootstrap.ControlLabel>
                <Bootstrap.FormControl id="selectEvent" componentClass="select" placeholder="Select event" onChange={this.handleSelectEventChange.bind(this)}>
                    {event_options}
                </Bootstrap.FormControl>
            </Bootstrap.FormGroup>);
        }
    }

    showActionsSelect(){
        var action_options=this.state.actionsPerApp.map(function(action, index){
            return (<option value={action}>{action}</option>);
        });

        if(this.state.actionsPerApp.length==0){
            return(
            <Bootstrap.FormGroup disabled>
                <Bootstrap.ControlLabel disabled>Select action</Bootstrap.ControlLabel>
                <Bootstrap.FormControl id="selectAction" componentClass="select" placeholder="Select action" onChange={this.handleSelectActionChange.bind(this)} disabled>
                    {action_options}
                </Bootstrap.FormControl>
            </Bootstrap.FormGroup>);
        }
        else{
            return(
            <Bootstrap.FormGroup>
                <Bootstrap.ControlLabel>Select action</Bootstrap.ControlLabel>
                <Bootstrap.FormControl id="selectAction" componentClass="select" placeholder="Select action" onChange={this.handleSelectActionChange.bind(this)}>
                    {action_options}
                </Bootstrap.FormControl>
            </Bootstrap.FormGroup>);
        }
    }

    showModalButtons(){
        if(this.state.stepIndex == 3){
            return (
                <Bootstrap.ButtonGroup>
                    <Bootstrap.Button bsStyle='primary' onClick={this.addTrigger} style={{marginRight: '5px'}}>
                         Submit
                    </Bootstrap.Button>
                    <Bootstrap.Button onClick={()=> this.closeModal()}>
                        Close
                    </Bootstrap.Button>
                </Bootstrap.ButtonGroup>
            );
        }

        else {
            return (
                <Bootstrap.ButtonGroup>
                    <Bootstrap.Button bsStyle='primary' onClick={this.nextStep} style={{marginRight: '5px'}}>
                        <Bootstrap.Glyphicon glyph='menu-right'></Bootstrap.Glyphicon> Next step</Bootstrap.Button>
                    <Bootstrap.Button onClick={()=> this.closeModal()}>
                        Close
                    </Bootstrap.Button>
                </Bootstrap.ButtonGroup>
            );
        }
    }

    showArgumentMapSelect(){
        var me=this;
        if(me.state.selectedAction.hasOwnProperty('arguments') && me.state.selectedEvent.hasOwnProperty('arguments')){
            var action_args=me.state.selectedAction.arguments;
            var event_args=me.state.selectedEvent.arguments;
            var elements=[];
            action_args.forEach(function(action_arg){
                
                var element_options=[];
                event_args.forEach(function(event_arg, index){
                    element_options.push(
                        <option value={event_arg.name}>{event_arg.name}</option>
                    );
                });

                element_options.push(
                    <option value="No mapping">No mapping</option>);

                elements.push(
                    <Bootstrap.FormGroup>
                        <Bootstrap.ControlLabel>{action_arg.name}</Bootstrap.ControlLabel>
                        <Bootstrap.FormControl id={action_arg.name} componentClass="select">
                            {element_options}
                        </Bootstrap.FormControl>
                    </Bootstrap.FormGroup>
                );
            });
            return elements;
        }
    }

    formArgumentMap(){
        var me=this;
        var args_map={};
        if(me.state.selectedAction.hasOwnProperty('arguments') && me.state.selectedEvent.hasOwnProperty('arguments')){
            console.log('IN');
            var action_args=me.state.selectedAction.arguments;
            var event_args=me.state.selectedEvent.arguments;
            action_args.forEach(function(action_arg){             
                var select_element_value=document.getElementById(action_arg.name).value;
                if(select_element_value == 'No mapping'){
                }
                else{
                    args_map[action_arg.name]=select_element_value;
                }
            });
        }
        console.log('Args Map: ', args_map);
        return args_map;
    }

    formTriggerJSON(){
        var me=this;
        var data={};
        var args_map=this.formArgumentMap();
        data['donor_app']=me.state.selectedDonorApp;
        data['receiver_app']=me.state.selectedReceiverApp;
        var trigger={};
        trigger['event_name']=me.state.selectedEvent.func_group+"."+me.state.selectedEvent.func_name;
        trigger['conditions']=[];
        trigger['actions']=[{"args_map": args_map, "func_name": me.state.selectedAction.func_name}]
        data['trigger']=trigger;
        console.log(data);
        return data;
    }

    render() {
        var me=this;
        var loading = this.state.loading;
        var app_options=this.state.apps.map(function(app, index){
            return (<option value={app.name}>{app.name}</option>);
        }); 

        return (
                <div>
                    {loading && getSpinner()}
                    <div style={this.props.style} className="card">
                        <div className="card-body">
                            <table className="table striped">
                                <thead>
                                    <tr className="reactable-filterer">
                                        <td>
                                            <h4>Integrations</h4>
                                        </td>
                                        <td style={{textAlign: 'right'}}>                         
                                            <Bootstrap.Button onClick={()=> this.openTriggerModal()}>
                                                <Bootstrap.Glyphicon glyph='plus' />
                                                Create trigger
                                            </Bootstrap.Button>
                                        </td>
                                    </tr>
                                </thead>
                            </table>

                            <div id="mynetwork"></div>

                            <Bootstrap.Modal show={this.state.showModal} onHide={this.closeModal}>
                                <Bootstrap.Modal.Header>
                                    <Bootstrap.Modal.Title> Add Trigger</Bootstrap.Modal.Title>
                                </Bootstrap.Modal.Header>
                               
                                <Bootstrap.Modal.Body>
                                    <Bootstrap.Tabs id="tabs" activeKey={this.state.stepIndex}>
                                        
                                        <Bootstrap.Tab eventKey={1} title="Step 1">
                                            
                                            <Bootstrap.FormGroup>
                                                <Bootstrap.ControlLabel>Select Donor app</Bootstrap.ControlLabel>
                                                <Bootstrap.FormControl id="selectDonorApp" componentClass="select" placeholder="Select donor app" onChange={this.handleSelectDonorAppChange.bind(this)}>
                                                    {app_options}
                                                </Bootstrap.FormControl>
                                            </Bootstrap.FormGroup>

                                            {this.showEventsSelect()}
                                        </Bootstrap.Tab>

                                        <Bootstrap.Tab eventKey={2} title="Step 2">
                                             <Bootstrap.FormGroup>
                                                <Bootstrap.ControlLabel>Select Receiver app</Bootstrap.ControlLabel>
                                                <Bootstrap.FormControl id="selectReceiverApp" componentClass="select" placeholder="Select Receiver app" onChange={this.handleSelectReceiverAppChange.bind(this)}>
                                                    {app_options}
                                                </Bootstrap.FormControl>
                                            </Bootstrap.FormGroup>

                                            {this.showActionsSelect()}

                                        </Bootstrap.Tab>
                                        <Bootstrap.Tab eventKey={3} title="Step 3">
                                            <h5>Arguments map</h5>
                                            <hr/>
                                            <div>{/*<h4>Donor app: {this.state.selectedDonorApp}</h4>
                                            <h4>Receiver app: {this.state.selectedReceiverApp}</h4>
                                            <h4>Event: {JSON.stringify(this.state.selectedEvent)}</h4>
                                            <h4>Action: {JSON.stringify(this.state.selectedAction)}</h4>*/}</div>
                                            {this.showArgumentMapSelect()}
                                        </Bootstrap.Tab>
                                    </Bootstrap.Tabs>
                                
                                </Bootstrap.Modal.Body>

                                <Bootstrap.Modal.Footer>
                                    {this.showModalButtons()}
                                </Bootstrap.Modal.Footer>

                            </Bootstrap.Modal>

                            <br/>
                        </div>
                    </div>
                </div>);
}
}

module.exports = connect(state => {
    return { auth: state.auth, alert: state.alert };
})(Integrations);