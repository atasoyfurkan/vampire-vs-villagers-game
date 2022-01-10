import argparse
import json
import socket
import select
from threading import Thread
import random
import time
import logging

PORT = 12345
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    HOST = s.getsockname()[0]

args = None
clients = {}

logging.warning('Watch out!')


def main():
    global args
    args = init_argparse()
    print(args)

    listen_handshake()
    print("Number of clients:", len(clients), "Names:", clients.keys())
    choose_vampire()
    acknowledge_clients_about_roles()
    print("EXECUTED acknowledge_clients_about_roles()")

    while(True):
        broadcast_game_state("daytime")
        print('EXECUTED broadcast_game_state("daytime")')
        time.sleep(args.daytime_duration)  # wait for daytime

        broadcast_game_state("votetime")
        print('EXECUTED broadcast_game_state("votetime")')
        votes = listen_votes()  # wait for votetime
        print("INFO Total vote count:", len(votes))
        hanged_client = count_votes(votes)
        print("INFO Hanged client:", hanged_client)
        kill_client(hanged_client, "hanged")
        print("INFO Killed client:", hanged_client)

        is_game_ended, winner = check_and_broadcast_game_ended()
        if is_game_ended:
            print(f"Game ended. Winner is {winner}")
            break

        broadcast_game_state("nighttime")
        print('EXECUTED broadcast_game_state("nighttime")')
        attacked_client = listen_vampire()  # wait for nighttime
        print("INFO Attacked client:", attacked_client)
        kill_client(attacked_client, "attacked")
        print("INFO Killed client:", attacked_client)
        is_game_ended, winner = check_and_broadcast_game_ended()
        if is_game_ended:
            print(f"Game ended. Winner is {winner}")
            break


def init_argparse():
    # Initialize parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--daytime_duration", default=120, type=int, help="Set Daytime Duration")
    parser.add_argument("--votetime_duration", default=30, type=int, help="Set Vote Time Duration")
    parser.add_argument("--nighttime_duration", default=30, type=int, help="Set Nighttime Duration")
    parser.add_argument("--number_of_users", default=5, type=int, help="Set Number of Users")

    args = parser.parse_args()

    return args


def send_tcp(message, client_ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TCP
            s.connect((client_ip, PORT))
            s.sendall(str.encode(message))
    except Exception as e:
        print("An error occured:", e)


def listen_handshake():
    while(len(clients) < args.number_of_users):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:  # UDP
                s.bind(('', PORT))
                s.setblocking(0)
                result = select.select([s], [], [])
                output, (client_ip, _) = result[0][0].recvfrom(10240)

            content = json.loads(output.decode("utf-8"))
            if content["type"] == 1:
                get_discover(content, client_ip)
                print("INFO Handshaked with client:", content['client_name'])
        except Exception as e:
            print("An error occured:", e)


def get_discover(content, client_ip):
    global clients

    client_name = content["client_name"]
    client_burst_id = content["ID"]

    if len(clients) < args.number_of_users:  # Ignore if the capacity is full
        if client_name not in clients:  # first discover
            clients[client_name] = {
                "IP": client_ip,
                "ID": client_burst_id,
                "is_vampire": False,
                "is_dead": False
            }
            send_discover_response(client_ip)
            # Thread(target=send_discover_response, args=[client_ip]).start()

        elif clients[client_name]["ID"] != client_burst_id:  # discover from the same user (connection lost)
            send_discover_response(client_ip)
            # Thread(target=send_discover_response, args=[client_ip]).start()


def send_discover_response(client_ip):
    message = json.dumps({
        "type": 2
    })
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TCP
            s.connect((client_ip, PORT))
            s.sendall(str.encode(message))
    except Exception as e:
        print("An error occured:", e)


def choose_vampire():
    global clients

    vampire_id = random.randint(0, args.number_of_users-1)
    vampire_name = list(clients.keys())[vampire_id]
    clients[vampire_name]["is_vampire"] = True
    print("INFO Vampire is:", vampire_name)


def acknowledge_clients_about_roles():
    global clients

    for client_features in clients.values():
        client_ip = client_features['IP']
        is_vampire = client_features['is_vampire']

        message = json.dumps({
            "type": 3,
            "role": "vampire" if is_vampire else "villager"
        })
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TCP
                s.connect((client_ip, PORT))
                s.sendall(str.encode(message))
        except Exception as e:
            print("An error occured:", e)


def broadcast_game_state(state):  # daytime or votetime or nighttime
    duration = None
    if state == "daytime":
        duration = args.daytime_duration
    elif state == "votetime":
        duration = args.votetime_duration
    elif state == "nighttime":
        duration = args.nighttime_duration

    message = json.dumps({
        "type": 3,
        "state": state,
        "duration": duration
    })
    for client_features in clients.values():
        client_ip = client_features["IP"]
        send_tcp(message, client_ip)


def listen_votes():  # TODO test timeout
    start_time = time.time()
    votes = {}

    while(time.time() - start_time < args.votetime_duration):
        # try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:  # UDP
            s.bind(('', PORT))
            remaining_time = args.nighttime_duration - (time.time() - start_time)
            s.settimeout(remaining_time)
            s.setblocking(0)
            result = select.select([s], [], [], remaining_time)
            if len(result[0]) > 0:
                output, (client_ip, _) = result[0][0].recvfrom(10240)

        if len(result[0]) > 0:
            content = json.loads(output.decode("utf-8"))
            if content["type"] == 5:
                voter_name, voted_name = get_vote(content, client_ip)
                print(f"INFO client {voter_name} voted for {voted_name}")
                if voter_name:
                    votes[voter_name] = voted_name
        # except Exception as e:
        #     print("An error occured:", e)

    return votes


def get_vote(content, voter_client_ip):
    voted_name = content["voted_client_name"]

    for client_name, client_features in clients.items():
        client_ip = client_features['IP']

        if client_ip == voter_client_ip:
            voter_name = client_name
            break

    return voter_name, voted_name


def count_votes(votes):
    vote_of_clients = {}
    for voted_client in votes.values():
        if vote_of_clients.get(voted_client):
            vote_of_clients['vote'] += 1
        else:
            vote_of_clients['vote'] = 0

    if(len(vote_of_clients) > 0):  # if there is any voted user
        hanged_name = max(vote_of_clients, key=vote_of_clients.get)

    else:  # if there is not any vote, hang one randomly
        unlucky_id = random.randint(0, args.number_of_users-1)
        hanged_name = list(clients.keys())[unlucky_id]

    return hanged_name


def kill_client(name, status):  # status = "hanged" or "attacked"
    if clients.get(name):
        clients[name]["is_dead"] = True

        if status == "hanged":
            message = json.dumps({
                "type": 6,
                "hanged_client_name": name
            })
        elif status == "attacked":
            message = json.dumps({
                "type": 9,
                "attacked_client_name": name
            })

        for client_features in clients.values():
            client_ip = client_features["IP"]
            send_tcp(message, client_ip)


def check_and_broadcast_game_ended():
    alive_villagers_count = 0
    alive_vampires_count = 0

    for client_features in clients.values():
        is_vampire = client_features['is_vampire']
        is_dead = client_features['is_dead']

        if is_vampire and not is_dead:
            alive_vampires_count += 1

        if not is_vampire and not is_dead:
            alive_villagers_count += 1

    is_game_ended = False
    winner = ""

    if alive_vampires_count == 0:
        is_game_ended = True
        winner = "villagers"

    if alive_villagers_count == alive_vampires_count:
        is_game_ended = True
        winner = "vampire"

    message = json.dumps({
        "type": 7,
        "winner": winner
    })
    for client_features in clients.values():
        client_ip = client_features["IP"]
        send_tcp(message, client_ip)

    print("Alive vampires:", alive_vampires_count, "Alive villagers:", alive_villagers_count)

    return is_game_ended, winner


def listen_vampire():  # TODO test timeout
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TCP
            s.bind((HOST, PORT))
            s.settimeout(args.nighttime_duration)  # timeout for the vampire kill command
            s.listen()
            conn, client_ip = s.accept()
            with conn:
                output = conn.recv(10240)

            content = json.loads(output.decode("utf-8"))
            if content["type"] == 8:
                attacked_client = content['attacked_client_name']
    except Exception as e:
        print("An error occured:", e)

    return attacked_client


if __name__ == "__main__":
    main()
