## Challenges
### Implementing Awe Feature
Our project included an additional challenge of conducting a DDOS attack on the host so that it resulted in at least %10 packet loss. This task required generating and overloading the host with significant amount of packets, for which we used threading library. While the determining the rate and sizes of the packet bursts required some eyeball estimation, we also had to ensure that the packet loss in our network was not related to external causes like socket mishandling. In addition, to test and demonstrate this feature, we implemented a special run configuration in our client script.
### Designing the network
While we had some experience programming P2P networks with Workshops, our project had many new challenges due to its structure. Even though we borrowed some tools and structures from the previous Workshops, we created most of the mechanisms for the game control and message protocol from scratch. 
Unlike Workshop assignments, our game required asymmetric communication mechanisms to track game state, time countes and process actions that would affect multiple clients at once so we implemented two scripts with distinct roles as the host and client. Since we also had to share the workload, (for which we decided to split as the client and host script implementation) our project required a sharp project plan and desing outline of the game mechanics and tasks of the client and host scripts. To be on the same page before starting on the implementation, we had to sketch the project plan early.
### Implementing GUI
Initially, we had decided to stick with a simple UI to focus on the network aspects of our game. While our original CLI of our game worked adequately, extension provided to us has led us to explore GUI libraries to add some icing on the cake. While we found a simplistic GUI library called PySimpleGUI, there was still a learning phase as we had very little experience in GUI development.
### Testing & Demo 
One of the most challenging part of this project was actually the testing. Since the had a more complex structure, there were many edge cases during the testing. Also, since our testing all of the features of the game required at least 4 participants, setting up the full testing environment was also problematic. Likewise, recording the demo was also quite difficult in terms of logistics. Since we only had small windows for beta testing and recording the demo, we had to be write code accurately and concisely.

## Berke: Personal Effort
* Wrote client.py, client_gui.py
* Wrote Challenges part of README.md
* Contributed to final presentation and demo