/*
    This file is part of PESPad.

    PESPad allows any device that can run a web browser to be used as
    control pad for Linux based operating systems.

    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)

    PESPad is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PESPad is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PESPad.  If not, see <http://www.gnu.org/licenses/>.
*/

function setTitle(s){
	Ext.getCmp('titleBar').setTitle(s);
}

var screenStack = new Array();
screenStack.push({ panel: 'welcomePanel', title: 'PES Home' });

new Ext.Application({
	launch: function() {

		function btnPress(btn){
			Ext.Ajax.request({
				failure: function(response, opts){
					Ext.Msg.alert("Error!", "Failed to send button: " + btn);
				},
				method: 'GET',
				success: function(response, opts){
					var json = Ext.util.JSON.decode(response.responseText);
					if (!json.success){
						Ext.Msg.alert("Error!", json.error);
					}
				},
				url: '/js/' + btn
			});
		}

		function createBtn(text, action, width, height, margin){
			if (!margin){
				margin = 0;
			}

			return new Ext.Button({
				height: height,
				listeners: {
					render: function(){
						el = this.getEl().dom;
						if (el.addEventListener){
							el.addEventListener('mousedown', function(){ btnPress(action) }, false);
							el.addEventListener('mouseup', function(){ btnPress(action) }, false);
							el.addEventListener('touchstart', function(){ btnPress(action) }, false);
							el.addEventListener('touchend', function(){ btnPress(action) }, false);
						}
						else{
							el.attachEvent('mousedown', function(){ btnPress(action) });
							el.attachEvent('mouseup', function(){ btnPress(action) });
							el.attachEvent('touchstart', function(){ btnPress(action) });
							el.attachEvent('touchend', function(){ btnPress(action) });
						}
					}
				},
				renderTo: action + 'Btn',
				style: {
					margin: margin + 'px'
				},
				text: text,
				ui: 'small',
				width: width
			});
		}

		function mouseDown(event){
			console.log('mouse down');
		}

		function mouseUp(event){
			console.log('mouse up');
		}

		var btnWidth = 40;
		var btnHeight = 40;

		var joystickPanel = new Ext.Panel({
			dockedItems: [
				{
					dock: 'top',
					id: 'titleBar',
					items: [
						{
							handler: function(){
								Ext.Ajax.request({
									failure: function(response, opts){
										Ext.Msg.alert("Error!", "Failed to request a joystick device from PES");
									},
									method: 'GET',
									success: function(response, opts){
										var json = Ext.util.JSON.decode(response.responseText);
										if (!json.success){
											Ext.Msg.alert("Error!", json.error);
										}
										else{
											Ext.get('connectBtn').setVisible(false);
											Ext.get('disconnectBtn').setVisible(true);
											Ext.Msg.alert("Info", "Joystick connected!");
										}
									},
									url: '/js/connect'
								});
							},
							id: 'connectBtn',
							text: 'Connect'
						},{
							handler: function(){
								Ext.Ajax.request({
									failure: function(response, opts){
										Ext.Msg.alert("Error!", "Failed to process disconnect request!");
									},
									method: 'GET',
									success: function(response, opts){
										var json = Ext.util.JSON.decode(response.responseText);
										if (!json.success){
											Ext.Msg.alert("Error!", json.error);
										}
										else{
											Ext.get('connectBtn').setVisible(true);
											Ext.get('disconnectBtn').setVisible(false);
											Ext.Msg.alert("Info", "Disconnected ok!");
										}
									},
									url: '/js/disconnect'
								});
							},
							hidden: true,
							id: 'disconnectBtn',
							text: 'Disconnect'
						}
					],
					title: 'PESPad',
					ui: 'light',
					xtype: 'toolbar'
				}
			],
			fullscreen: true,
			id: 'joystickPanel',
			items: [
				{
					height: 40,
					contentEl: 'shoulderButtons',
					xtype: 'panel'
				},
				{
				
					height: 100,
					items: [
						{
							flex: 1,
							contentEl: 'dpad',
							xtype: 'panel'
						},{
							flex: 1,
							contentEl: 'startSelect',
							xtype: 'panel'
						},{
							flex: 1,
							contentEl: 'buttons',
							xtype: 'panel'
						}
					],
					layout: {
						align: 'center',
						type: 'hbox'
					},
					width: '100%',
					xtype: 'panel'
				}
			],
			layout: {
				align: 'center',
				pack: 'start',
				type: 'vbox'
			}
		});

		createBtn('Start', 'start', 55, 30, 5);
		createBtn('Select', 'select', 55, 30, 5);
		createBtn('Exit', 'exit', 55, 30, 5);
		createBtn('Save', 'save', 55, 30, 5);
		createBtn('Load', 'load', 55, 30, 5);
		createBtn('A', 'a', btnWidth, btnHeight);
		createBtn('B', 'b', btnWidth, btnHeight);
		createBtn('X', 'x', btnWidth, btnHeight);
		createBtn('Y', 'y', btnWidth, btnHeight);
		createBtn('<', 'left', btnWidth, btnHeight);
		createBtn('>', 'right', btnWidth, btnHeight);
		createBtn('/\\', 'up', btnWidth, btnHeight);
		createBtn('\\/', 'down', btnWidth, btnHeight);
		createBtn('L2', 'l2shoulder', btnWidth * 2, btnHeight, 5);
		createBtn('L1', 'l1shoulder', btnWidth * 2, btnHeight, 5);	
		createBtn('R1', 'r1shoulder', btnWidth * 2, btnHeight, 5);
		createBtn('R2', 'r2shoulder', btnWidth * 2, btnHeight, 5);
	}
});
