from os import wait
import socket
import threading
import select
import queue
import time
import json
import os
class Data:
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
        while Data.run_message_daemon:
            try:s.bind(('',12345))
            except OSError:pass
            s.setblocking(0)
            result = select.select([s],[],[])
            data,addr=result[0][0].recvfrom(10240)
            try: data=json.loads(data.decode("utf-8"))
            except: continue
            process_message(data,addr[0])


@threaded
def read_tcp_messages():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #This is to enable socket reusage since connections are dropped and reestablished in short intervals.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while Data.run_message_daemon:
            try: s.bind((Data.CLIENT_IP, 12345))
            except OSError: pass
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
            s.connect((ip, Data.CLIENT_PORT))
        except OSError:
            print("could not send message " + message)
            return
        s.sendall(byte_message)


@threaded
def send_udp_message(ip,message,burst_length=1):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(0,burst_length):
            byte_message=str(message).encode("utf-8")
            s.sendto(byte_message,(ip,Data.CLIENT_PORT))

@threaded
def send_broadcast_message(message,burst_length=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('',0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
    byte_message=str(message).encode("utf-8")
    for i in range(0,burst_length):
        s.sendto(byte_message,('<broadcast>',Data.CLIENT_PORT))

def get_ip_from_name(name):
    for ip in Data.ip_name_map.values():
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
        Data.game_start_event.set()
    elif message["type"]==4:
        Data.game_state=message["state"]
        print("Current phase: %s, Time Remaining %d"%(Data.game_state,message["duration"]))
        pass
    elif message["type"]==6:
        hanged_client=message["hanged_client_name"]
        if hanged_client==Data.client_name:
            Data.is_alive=False
            print("You have been voted off and hanged.")
        else:
            del Data.ip_name_map[get_ip_from_name(hanged_client)]
            print("%s is voted off and hanged")
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
            print("%s is killed by the vampire")
    elif message["type"]==10:
        if sender_ip == Data.CLIENT_IP:
            pass
        else: 
            print("%s: %s"%(Data.ip_name_map[sender_ip],message["body"]))

@threaded
def initiate_awe():
    while Data.game_state=="votetime":
        udp_threads=[]
        for i in range(0,50):
            udp_threads.append(send_udp_message(Data.host_ip,"Let there be no votes",50))
        for thread in udp_threads:
            thread.join()
        time.sleep(0.1)

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
                send_broadcast_message(vote_message)
            elif Data.game_state=="votetime":
                tokens=command.split(" ")
                if tokens[0]=="vote":
                    vote_message=json.dumps({"type":5,"voted_client_name":tokens[1]})
                    send_udp_message(Data.host_ip,vote_message)
                if tokens[0]=="awe":
                    if Data.client_role=="vampire" and not Data.awe_used:
                        Data.awe_used=True
                        initiate_awe()
            elif Data.game_state=="nighttime":
                    tokens=command.split(" ")
                    if tokens[0]=="kill":
                        kill_message=json.dumps({"type":8,"attacked_client_name":tokens[1]})
                        send_tcp_message(Data.host_ip,kill_message)


def main():
    Data.client_name=input("Enter name: ")
    #TODO: Broadcast message will be sent with necessary format
    read_tcp_messages()
    read_udp_messages()
    current_time=int(time.time()*1000)
    broadcast_message=json.dumps({"type":1,"client_name":Data.client_name,"ID":current_time})
    send_broadcast_message(broadcast_message,10)
    #TODO: Wait for response from the host
    if Data.join_response_event.wait(2):
        #TODO: If yes, continue to wait for game start.
        Data.game_start_event.wait()
        input_cycle()
        read_inputs()
    else: #Otherwise, exit
        print("No active host is found, exiting the app...")
        os._exit(0)


if __name__ == "__main__":
    main()