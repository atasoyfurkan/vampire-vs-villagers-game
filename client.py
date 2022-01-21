from ntpath import join
from os import wait
import socket
import threading
import select
import sys
import queue
import time
import json
import os
class Data:
    HOST_PORT=12346
    CLIENT_PORT=12345
    CLIENT_IP=""
    
    client_name=""
    ip_name_map={}
    game_state="initial"
    
    host_ip=""
    client_role="villager"

    run_message_daemon=True
    input_queue=queue.Queue()
    
    host_message_queue=queue.Queue()
    chat_message_queue=queue.Queue()
    
    game_end=False

    is_alive=True
    awe_used=False
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
        print("Game starts, you are %s"%(Data.client_role))
        print("Active players:")
        for name in Data.ip_name_map.values():
            print(name)
        Data.game_start_event.set()
    elif message["type"]==4:
        Data.game_state=message["state"]
        print("Current phase: %s, Time Remaining %d"%(Data.game_state,message["duration"]))
        if Data.is_alive:
            if Data.game_state=="daytime":
                print("Enter any message to broadcast.")
            elif Data.game_state=="votetime":
                print("To vote, type: vote <client-name>")
                if Data.client_role=="vampire" and not Data.awe_used:
                    print("Awe skill awailable. To use, type: awe")
            elif Data.game_state=="nighttime":
                if Data.client_role=="vampire":
                    print("To kill a client, type: kill <client-name>")
        
    elif message["type"]==6:
        hanged_client=message["hanged_client_name"]
        if hanged_client==Data.client_name:
            Data.is_alive=False
            print("You have been voted off and hanged.")
        else:
            del Data.ip_name_map[get_ip_from_name(hanged_client)]
            print("%s is voted off and hanged"%(hanged_client))
    elif message["type"]==7:
        print("Game over, %s win!"%(message["winner"]))
        Data.game_end=True
        time.sleep(3)
        os._exit(0)
        pass
    elif message["type"]==9:
        killed_client=message["attacked_client_name"]
        if killed_client==Data.client_name:
            Data.is_alive=False
            print("You have been killed by the vampire.")
        else:
            del Data.ip_name_map[get_ip_from_name(killed_client)]
            print("%s is killed by the vampire"%(killed_client))
    elif message["type"]==10:
        if sender_ip == Data.CLIENT_IP:
            pass
        else: 
            print("%s: %s"%(Data.ip_name_map[sender_ip],message["body"]))

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
        command=input()
        Data.input_queue.put(command)

@threaded
def input_cycle():
    while not Data.game_end:
        try:
            command=Data.input_queue.get()
        except:
            command=None
        
        if command and Data.is_alive:
            if Data.game_state=="daytime":
                vote_message=json.dumps({"type":10,"body":command})
                send_broadcast_message(vote_message,Data.CLIENT_PORT)
            elif Data.game_state=="votetime":
                tokens=command.split(" ")
                if tokens[0]=="vote":
                    vote_message=json.dumps({"type":5,"voted_client_name":tokens[1]})
                    send_udp_message(Data.host_ip,vote_message,Data.HOST_PORT)
                if tokens[0]=="awe":
                    if Data.client_role=="vampire" and not Data.awe_used:
                        Data.awe_used=True
                        initiate_awe()
                        print("Initiating awe...")
            elif Data.game_state=="nighttime":
                    tokens=command.split(" ")
                    if tokens[0]=="kill":
                        kill_message=json.dumps({"type":8,"attacked_client_name":tokens[1]})
                        send_tcp_message(Data.host_ip,kill_message)
def test_ddos_read():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:s.bind(('',Data.CLIENT_PORT))
        except OSError:pass
        s.setblocking(0)
        counter=0
        while Data.run_message_daemon:
            result = select.select([s],[],[],5)
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
                test_ddos_send(sys.argv[2],int(sys.argv.get(3,"100")),float(sys.argv.get(4,"0.1")))
            os._exit(0)
        
    Data.client_name=input("Enter name: ")
    read_tcp_messages()
    read_udp_messages()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        Data.CLIENT_IP = s.getsockname()[0]
    
    current_time=int(time.time()*1000)
    broadcast_message=json.dumps({"type":1,"client_name":Data.client_name,"ID":current_time})
    #Broadcast message will be sent with necessary format
    send_broadcast_message(broadcast_message,Data.HOST_PORT,10)
    #Wait for response from the host
    if Data.join_response_event.wait(2):
        #If yes, continue to wait for game start.
        Data.game_start_event.wait()
        input_cycle()
        read_inputs()
    else: #Otherwise, exit
        print("No active host is found, exiting the app...")
        os._exit(0)


if __name__ == "__main__":
    main()