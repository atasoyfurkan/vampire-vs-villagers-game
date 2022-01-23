# vampire-vs-villagers-game
## User Manual
* To run the client script, run command ```python3 client_gui.py```
* To run the DdoS test, you need to have at least two computers, one to listen and other to send:
  * For the listener, run ```python3 client_gui.py test_ddos listen```
  * For the sender, run ```python3 client_gui.py test_ddos <listener-ip> <test-packet-count> <delay>```
    * ```<test-packet-count>``` is to determine number of test packets to send during the DdoS attack, listener will count these packets.
    * ```<delay>``` is to determine delay between test packets.
    * Default values are 100 and 0.1 respectively. 

## Objectives

### Create a multiplayer game works on LAN

- Our first objective is creating a multiplayer game which works on Local Area Network. We aimed to implement the communication processes with UDP and TCP messages on local network so that users can play with each other.

### Create A Fun Game

- Our second objective is that the game needs to be enjoyable so we planned the roles and the functionalities of the role to make it fun.

### Implementing DDOS Attack

- Our third objective is implementation of the DDOS attack for a functionality in the game. In this way, we plan to improve our perspective on the network and make the game more fun.

### **Implementing GUI**

- Our last objective is implementation of GUI which makes game more playable also cool design can attract people to play the game.


## Challenges

### Designing the Game & Network
While we had some experience programming P2P networks with Workshops, our project had lots of new aspects due to its structure. Even though we borrowed some tools and structures from the previous Workshops, we created most of the mechanisms for the game control and message protocol from scratch. 
Unlike Workshop assignments, our game also required asymmetric communication mechanisms to track game state, time counters and process actions that would affect multiple clients at once so we implemented two scripts with distinct roles as the host and client. Since we also had to share the workload, (for which we decided to split as the client and host script implementation) our project required a sharp project plan and a design outline of the game mechanics and tasks of the client and host scripts. To be on the same page before starting on the implementation, we had to sketch the game mechanics and project plan early.

### Implementing Awe Feature(DDOS)
Our project included an additional challenge of conducting a DDOS attack on the host so that it resulted in at least %10 packet loss. This task required generating and overloading the host with significant amount of packets, for which we used threading library. While implementing the functionality itself was not very difficult, determining the rate and sizes of the packet bursts required some eyeball estimation as there was a tradeoff between attack strength and CPU usage. We also had to ensure that the packet loss in our network was not related to external causes like socket mishandling. Additionaly, to test and demonstrate this feature, we implemented a special run configuration in our client script.

### Implementing GUI
Initially, we had decided to stick with a simple UI to focus on the network aspects of our game. While our original CLI of our game worked adequately, extension provided to us has led us to explore GUI libraries to add some icing on the cake. While we found a simplistic GUI library called PySimpleGUI, there was still a learning phase as we had very little experience in GUI development.

### Testing & Demo 
One of the most challenging part of this project was actually the testing. Since the had a more complex structure, there were many edge cases during the testing. Also, since our testing all of the features of the game required at least 4 participants, setting up the full testing environment was also problematic. Likewise, recording the demo was also quite difficult in terms of logistics. Since we didn't have much chance for beta testing and recording the demo, we had to write the code accurately and concisely.

## Berke: Personal Effort
* Wrote client.py, client_gui.py
* Wrote Challenges part of README.md
* Contributed to final presentation and demo

## Furkan: Personal Effort
- Wrote host.py
- Wrote Objectives part of README.md
- Contributed to final presentation and demo
