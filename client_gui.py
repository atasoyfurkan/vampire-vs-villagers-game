from lib2to3.pgen2 import token
import socket
import threading
import select
import sys
import queue
import time
import json
import os
import PySimpleGUI as sg

class Data:
    HOST_PORT=12346
    CLIENT_PORT=12345
    CLIENT_IP=""
    
    gui_theme="DarkBlack1"
    client_name=""
    ip_name_map={}
    game_state="initial"
    
    host_ip=""
    client_role="villager"

    run_message_daemon=True
    input_queue=queue.Queue()
    
    host_message_queue=queue.Queue()
    chat_message_queue=queue.Queue()
    
    game_messages=[]

    game_end=False
    game_end_message=""
    is_alive=True
    awe_used=False
    
    current_stage_time=0
    stage_start_time=time.time()


    join_response_event=threading.Event()
    game_start_event=threading.Event()
    
    state_change_event=threading.Event()
    

'''
This wrapper is from https://stackoverflow.com/questions/19846332/python-threading-inside-a-class/19846691#19846691
It basically generates a secondary function for the wrapped function, which automatically creates a Thread and starts the fuction.
So it basically enables me to skip writing 
	new_thread=thread.Thread(target=send_message,args(.,.),kwargs..)
	new_thread.start()
        for each funtion
'''
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

@threaded
def read_udp_messages():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:s.bind(('',Data.CLIENT_PORT))
        except OSError:pass
        s.setblocking(0)
        while Data.run_message_daemon:
            result = select.select([s],[],[])
            data,addr=result[0][0].recvfrom(10240)
            try: data=json.loads(data.decode("utf-8"))
            except: continue
            process_message(data,addr[0])

@threaded
def read_tcp_messages():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind((Data.CLIENT_IP, Data.CLIENT_PORT))
        except OSError: pass
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while Data.run_message_daemon:
            s.listen()
            conn, addr = s.accept()
            with conn:
                data = conn.recv(10240)
                if not data: continue
                try: data=json.loads(data.decode("utf-8"))
                except: continue
                process_message(data,addr[0])

@threaded
def send_tcp_message(ip,message):
    byte_message=message.encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((ip, Data.HOST_PORT))
        except OSError:
            print("could not send message " + message)
            return
        s.sendall(byte_message)

@threaded
def send_udp_message(ip,message,port,burst_length=1):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(0,burst_length):
            byte_message=str(message).encode("utf-8")
            try:s.sendto(byte_message,(ip,port))
            except:continue

@threaded
def send_broadcast_message(message,port,burst_length=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('',0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
    byte_message=str(message).encode("utf-8")
    for i in range(0,burst_length):
        s.sendto(byte_message,('<broadcast>',port))

def get_ip_from_name(name):
    for ip in Data.ip_name_map.keys():
        if name==Data.ip_name_map[ip]:
            return ip
    return None

def process_message(message,sender_ip):
    if message["type"]==2:
        Data.host_ip=sender_ip
        Data.join_response_event.set()
    elif message["type"]==3:
        Data.client_role=message["role"]
        Data.ip_name_map=message["client_names"]
        Data.game_messages.append("Game starts, you are %s"%(Data.client_role))
        Data.game_start_event.set()
    elif message["type"]==4:
        Data.game_state=message["state"]
        Data.stage_start_time=time.time()
        Data.current_stage_time=int(message["duration"])
        Data.game_messages.append("Stage change to %s, "%(Data.game_state))
    elif message["type"]==6:
        hanged_client=message["hanged_client_name"]
        if hanged_client==Data.client_name:
            Data.is_alive=False
            Data.game_messages.append("You have been voted off and hanged.")
        else:
            del Data.ip_name_map[get_ip_from_name(hanged_client)]
            Data.game_messages.append("%s is voted off and hanged"%(hanged_client))
    elif message["type"]==7:
        if message["winner"]=="vampire":
            Data.game_end_message="Game over, %s win!"%(message["winner"])
        else:
            Data.game_end_message="Game over, %s wins!"%(message["winner"])
        Data.game_end=True
    elif message["type"]==9:
        killed_client=message["attacked_client_name"]
        if killed_client==Data.client_name:
            Data.is_alive=False
            Data.game_messages.append("You have been killed by the vampire.")
            del Data.ip_name_map[get_ip_from_name(killed_client)]
        else:
            del Data.ip_name_map[get_ip_from_name(killed_client)]
            Data.game_messages.append("%s is killed by the vampire"%(killed_client))
    elif message["type"]==10:
        Data.game_messages.append("%s: %s"%(Data.ip_name_map[sender_ip],message["body"]))

@threaded
def initiate_awe():
    while Data.game_state=="votetime" or Data.game_state=="daytime":
        udp_threads=[]
        for i in range(0,50):
            udp_threads.append(send_udp_message(Data.host_ip,"Let there be no votes",1234,1000))
        for thread in udp_threads:
            thread.join()
        time.sleep(0.01)

@threaded
def read_inputs():
    while not Data.game_end:
        try: command=Data.input_queue.get()
        except: command=None
        if command and Data.is_alive:
            if Data.game_state=="daytime":
                tokens=command.split(' ')
                if tokens[0]=="/say" and len(command)>6:
                    vote_message=json.dumps({"type":10,"body":command[5:]})
                    send_broadcast_message(vote_message,Data.CLIENT_PORT)  
                if tokens[0]=="/awe":
                    if Data.client_role=="vampire" and not Data.awe_used:
                        Data.awe_used=True
                        initiate_awe()
                        Data.game_messages.append("Initiating awe...")
                    else:
                        Data.game_messages.append("You are not allowed to use /awe")
            elif Data.game_state=="votetime":
                tokens=command.split(" ")
                if len(tokens)>=2:
                    if tokens[0]=="/vote" and tokens[1] in get_alive_users():
                        vote_message=json.dumps({"type":5,"voted_client_name":tokens[1]})
                        send_udp_message(Data.host_ip,vote_message,Data.HOST_PORT)
                if tokens[0]=="/awe":
                    if Data.client_role=="vampire" and not Data.awe_used:
                        Data.awe_used=True
                        initiate_awe()
                        Data.game_messages.append("Initiating awe...")
                    else:
                        Data.game_messages.append("You are not allowed to use /awe")
            elif Data.game_state=="nighttime":
                    tokens=command.split(" ")
                    if len(tokens)>=2:
                        if tokens[0]=="/kill" and tokens[1] in get_alive_users():
                            kill_message=json.dumps({"type":8,"attacked_client_name":tokens[1]})
                            send_tcp_message(Data.host_ip,kill_message)
            else:
                Data.game_messages.append("Cannot execute command: %s" % command)

def get_available_commands():
    available_commands=[]
    if Data.is_alive:
        if Data.game_state=="daytime":
            available_commands.append("/say <message> : Broadcasts a chat message.")
            if Data.client_role=="vampire" and not Data.awe_used:
                available_commands.append("/awe : Initiate a DdoS attact on host to induce packet loss, can be used only once per game")
        elif Data.game_state=="votetime":
            available_commands.append("/vote <player-name> : Vote off a player to hang")
            if Data.client_role=="vampire" and not Data.awe_used:
                available_commands.append("/awe : Initiate a DdoS attact on host to induce packet loss, can be used only once per game")
        elif Data.game_state=="nighttime":
            if Data.client_role=="vampire":
                available_commands.append("/kill <player-name> : Kill a player")
    else:
        available_commands.append("You are dead but you can spectate.")
    return available_commands

def get_alive_users():
    return Data.ip_name_map.values()

def test_ddos_read():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:s.bind(('',Data.CLIENT_PORT))
        except OSError:pass
        s.setblocking(0)
        counter=0
        while Data.run_message_daemon:
            result = select.select([s],[],[],10)
            if not len(result[0]):
                print("Timeout, packets received: %s" % (counter))
                break
            data,_=result[0][0].recvfrom(10240)
            if data.decode("utf-8")=="end":
                print("Packets received: %s" % (counter))
                break
            else:
                counter+=1

def test_ddos_send(target_ip,packet_count=100,delay=0.1):
    Data.host_ip=target_ip
    Data.game_state="daytime"
    
    packet_count=int(packet_count)
    delay=float(delay)
    
    ddos_t=initiate_awe()
    time.sleep(1)
    for i in range(0,packet_count):
        t=send_udp_message(target_ip,"Is this reaching?",Data.CLIENT_PORT,1)
        t.join()
        time.sleep(delay)
    Data.game_state=""
    ddos_t.join()
    send_udp_message(target_ip,"end",Data.CLIENT_PORT,10).join()

def main(): 
    if len(sys.argv)>=3:
        if sys.argv[1]=="test_ddos":
            if sys.argv[2]=="listen":
                test_ddos_read()
            else:
                test_ddos_send(*(sys.argv[2:]))
            os._exit(0)
    else:
        start()

def start():
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        Data.CLIENT_IP = s.getsockname()[0]
    
    read_udp_messages()
    read_tcp_messages()
    
    sg.theme(Data.gui_theme)
    layout = [  [sg.Text('Welcome to Vampire & Villagers')],
                [sg.Text('Enter your name'), sg.Input('', enable_events=True,  key='-INPUT-', )],
                [sg.Button('Ok',bind_return_key=True), sg.Button('Exit')],
                [sg.ML(size=(100, 5), key='-TEXTBOX-')]
            ]
    window = sg.Window('Vampire vs Villagers', layout)
    messages=[]
    message_txt=window["-TEXTBOX-"]
    while True:             
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            window.close()
            os._exit(0)
        elif event=="Ok":
            Data.client_name=values["-INPUT-"]
            break
    
    broadcast_message=json.dumps({"type":1,"client_name":Data.client_name,"ID":int(time.time()*1000)})
    send_broadcast_message(broadcast_message,Data.HOST_PORT,10) #Broadcast message is sent
    
    messages.append("Broadcast message is sent, waiting for response...")
    message_txt.Update('\n'.join(messages))
    window.refresh()
    #Wait for response from the host for 2s
    if Data.join_response_event.wait(2):
        pass
    else:  
        messages.append("No active host is found, exiting the app...")
        message_txt.Update('\n'.join(messages))
        window.refresh()
        time.sleep(3)
        window.close()
        os._exit(0)
    
    messages.append("Response received, waiting for other players...")
    message_txt.Update('\n'.join(messages))
    window.refresh()
    
    while True:
        if Data.game_start_event.wait(0.1):
            break
        else:
            event, values = window.read(0.1)
            if event in (sg.WIN_CLOSED, 'Exit'):
                window.close()
                return
    
    window.close()
    core_game()

def core_game():
    
    read_inputs()
    
    sg.theme(Data.gui_theme)
    sg.theme_background_color('black')
    stage_image=sg.Image('img/%s_image.png'%(Data.game_state),size=(30,40))
    role_text=sg.Text("Role: %s"% (Data.client_role))
    current_stage_text=sg.Text("Current Stage: %s"%(Data.game_state))
    chatbox=sg.ML('\n'.join(Data.game_messages),size=(100, 40), key='-CHATBOX-')
    active_users_box=sg.ML('\n'.join(get_alive_users()),size=(10,40))
    input_help_box=sg.ML('\n'.join(get_available_commands()),size=(90,6))
    timeleft= Data.current_stage_time-int(time.time()-Data.stage_start_time)
    counter=sg.Text("Stage Ends in : %s s"%(timeleft))
    
    command_input=sg.InputText(size=(90,1),do_not_clear=True,key="COMMAND")
    
    layout = [[sg.Column([[role_text,current_stage_text,counter],[stage_image]]),
              sg.Column([[chatbox,active_users_box],
              [sg.Text("Available commands:"),input_help_box],
              [sg.Text("Enter command:"),command_input,sg.Button('Ok',bind_return_key=True)]])
    ]]
    
    window = sg.Window('Vampire vs Villagers',layout,resizable=True)
    last_state=""
    while True:
        event,values=window.read(0.5)
        if last_state!=Data.game_state:
            last_state=Data.game_state
            current_stage_text.update("Current Stage: %s"%(Data.game_state))
            stage_image.update('img/%s_image.png'%(Data.game_state))


        chatbox.update('\n'.join(Data.game_messages))
        active_users_box.update('\n'.join(get_alive_users()))
        input_help_box.update('\n'.join(get_available_commands()))
        timeleft= Data.current_stage_time-int(time.time()-Data.stage_start_time)
        counter.update("Stage Ends in : %ss"%(str(timeleft)))
        
        if event=="Ok":
            Data.input_queue.put(values["COMMAND"])
            command_input.update('')
        if Data.game_end:
            sg.popup(Data.game_end_message)
            window.close()
            break
    
    os._exit(0)

if __name__ == "__main__":
    main()