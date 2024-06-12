import asyncio
import websockets
import json
import random
import struct

# List to store connected players
players_no_room = []
rooms = {}
players_in_rooms = {}
players_websockets2ids = {}
players_ids2websockets = {}
id_counter = 0

players_disconnted = []

max_players_in_room = 2
max_errors = 6
possible_words = ['gustaw','miau','test']

# A - Joined_RoomInfo
# R - Room info
# C - can_start_game
# U - UpdateJoinedRoomInfo
# J - JoinRoom - Join
# G - GetRooms - Get
# Y - YourTurn - Your
# W - WaitTurn - Wait
# V - GameWin - Victory
# L - GameOver - Lose
# S - StartGame - Start
# P - UpdateWordProgress - Progress
# M - UpdateWrongLetters - Miss
# X - create_room 
# B - start_game
# D - delete_room
# C - guess_letter
# E - restart
# I - sendIndex/receiveIndex - Index 

# Function to handle incoming messages from clients
async def handle_message(websocket, path):
    global id_counter
    players_websockets2ids[websocket] = id_counter
    players_ids2websockets[id_counter] = websocket
    id_counter += 1

    players_no_room.append(getId(websocket))
    print("Player connected")
    room_info = getRoomInfo()
    await send_action(websocket, 'I', json.dumps({'index': getId(websocket)}))
    #await send_action(websocket, 'R', json.dumps({'rooms': room_info}))
    try:
        async for message in websocket:
            message, sign, action = decode_action(message)
            print("Received message", sign, action, message)
            if players_in_rooms.get(getId(websocket)) is None:
                if action == 'I':
                    old_index = decode_index(message)
                    index = getId(websocket)
                    print("Received index", index)
                    if old_index in players_disconnted:
                        players_websockets2ids[players_ids2websockets[index]] = None
                        players_ids2websockets[index] = None
                        players_websockets2ids[websocket] = old_index
                        players_ids2websockets[old_index] = websocket
                        print(getId(websocket))
                        print("Reconnected player", old_index)
                        await send_action(websocket, 'I', json.dumps({'index': getId(websocket)}))
                        print(getId(websocket) in players_in_rooms, rooms[players_in_rooms[getId(websocket)]]['state'] == 'waiting_to_start')
                        if getId(websocket) in players_in_rooms and rooms[players_in_rooms[getId(websocket)]]['state'] == 'waiting_to_start':
                            await send_action(websocket, 'A', json.dumps({'room_name': players_in_rooms[getId(websocket)], 'players': getNumOfPlayersInRoom(players_in_rooms[getId(websocket)]), 'max_players': max_players_in_room}))
                        elif getId(websocket) in players_in_rooms and rooms[players_in_rooms[getId(websocket)]]['state'] == 'playing':
                            await send_action(websocket,'S',json.dumps({'word_length': rooms[room_name]["word_length"], 'wordProgress': getWordProgress(rooms[room_name]["word"], rooms[room_name]["guessed_letters"])}))
                        
                elif action == 'X':
                    print("Room created")
                    room_name = decode_roomname(message)
                    if room_name not in rooms:
                        rooms[room_name] = {'players': [], 'state': 'waiting', 'word': json.dumps({}), 'word_length': 0, 'guessed_letters': [], 'host': getId(websocket)}
                        rooms[room_name]['players'].append(getId(websocket))
                        players_in_rooms[getId(websocket)] = room_name
                        players_no_room.remove(getId(websocket))  # Remove player from players_no_room list
                        await send_action(websocket, 'A', json.dumps({'room_name': room_name, 'players': 1, 'max_players': max_players_in_room}))
                    else:
                        await send_message(websocket, f'Room {room_name} already exists')
                    room_info = getRoomInfo()
                    for player in players_no_room:
                        print("TEST", player)
                        await send_action(getWebsocket(player), 'R', json.dumps({'rooms': room_info}))
                
                elif action == 'G':
                    room_info = getRoomInfo()
                    await send_action(websocket, 'R', json.dumps({'rooms': room_info}))

                elif action == 'J':
                    room_name = decode_roomname(message)
                    if room_name in rooms and len(rooms[room_name]['players']) < max_players_in_room:
                        print(f"Player joined room {room_name}")
                        rooms[room_name]['players'].append(getId(websocket))
                        players_in_rooms[getId(websocket)] = room_name
                        players_no_room.remove(getId(websocket))
                        await sendToAllPlayersInRoomExcept(room_name, getId(websocket), 'U', json.dumps({'players': getNumOfPlayersInRoom(room_name), 'max_players': max_players_in_room}))  #TODO do wszystkich oprócz websocket
                        await send_action(websocket, 'A', json.dumps({'room_name': room_name, 'players': getNumOfPlayersInRoom(room_name), 'max_players': max_players_in_room})) 
                        if getNumOfPlayersInRoom(room_name) == max_players_in_room:  # If the room now has two players 
                            rooms[room_name]['state'] = 'waiting_to_start'
                            await sendToHost(room_name, 'C', json.dumps({}))  # Send B action to the host
                        for player in players_no_room:
                            await send_action(getWebsocket(player), 'R', json.dumps({'rooms': room_info}))
            elif players_in_rooms[getId(websocket)] and rooms[players_in_rooms[getId(websocket)]]['state'] == 'waiting_to_start':
                if action == 'B':
                    print("Game started")
                    room_name = players_in_rooms[getId(websocket)]
                    rooms[room_name]["state"] = "playing"
                    rooms[room_name]["word"] = random.choice(possible_words)
                    rooms[room_name]["word_length"] = len(rooms[room_name]["word"])
                    rooms[room_name]["guessed_letters"] = []
                    rooms[room_name]["wrong_letters"] = []
                    rooms[room_name]["turn"] = 0
                    await send_action(getWebsocket(rooms[room_name]['players'][rooms[room_name]['turn']]), 'Y', json.dumps({}))  # Send action to the first player in the room
                    print("Word: ", rooms[room_name]["word"])

                    await sendToAllPlayersInRoom(room_name,'S',json.dumps({'word_length': rooms[room_name]["word_length"], 'wordProgress': getWordProgress(rooms[room_name]["word"], rooms[room_name]["guessed_letters"])}))
            elif getId(websocket) in players_in_rooms and rooms[players_in_rooms[getId(websocket)]]['state'] == 'playing':
                if action == 'C':
                    room_name = players_in_rooms[getId(websocket)]
                    letter = decode_letter(message)
                    print("Guess letter", letter)
                    word = rooms[room_name]['word']

                    if len(letter) == 1 and letter.isalpha():
                        if letter not in rooms[room_name]['guessed_letters'] and letter not in rooms[room_name]['wrong_letters']:
                            if checkIfLetterInWord(letter, word):
                                rooms[room_name]['guessed_letters'].append(letter)
                                if len(rooms[room_name]['guessed_letters']) == getUniqueLettersCount(word):
                                    rooms[room_name]["state"] = "ended"
                                    await sendToAllPlayersInRoom(room_name,'V', json.dumps({'word': word}))
                                else:
                                    await sendToAllPlayersInRoom(room_name,'P', json.dumps({'wordProgress': getWordProgress(word, rooms[room_name]['guessed_letters'])}))
                            else:
                                rooms[room_name]['wrong_letters'].append(letter)
                                if len(rooms[room_name]['wrong_letters']) == max_errors:
                                    rooms[room_name]["state"] = "ended"
                                    await sendToAllPlayersInRoom(room_name,'L', json.dumps({'word': word}))
                                else:
                                    await sendToAllPlayersInRoom(room_name,'M', json.dumps({'wrongLetters': rooms[room_name]['wrong_letters'], 'errors': len(rooms[room_name]['wrong_letters'])}))
                            
                            await send_action(getWebsocket(rooms[room_name]['players'][rooms[room_name]['turn']]), 'W', json.dumps({}))  
                            rooms[room_name]['turn'] = (rooms[room_name]['turn'] + 1) % max_players_in_room
                            await send_action(getWebsocket(rooms[room_name]['players'][rooms[room_name]['turn']]), 'Y', json.dumps({}))                 
                        else:
                            await send_message(websocket, 'Letter already guessed')
                    else:
                        await send_message(websocket, 'Invalid letter')
            elif  getId(websocket) in players_in_rooms and rooms[players_in_rooms[getId(websocket)]]['state'] == 'ended':
                if action == 'D':
                    print
                    room_name = players_in_rooms[getId(websocket)]
                    rooms[room_name]['players'].remove(getId(websocket))
                    del players_in_rooms[getId(websocket)]
                    players_no_room.append(getId(websocket))
                    
                    if len(rooms[room_name]['players']) == 0:
                        del rooms[room_name]

                    await send_action(websocket, 'E',json.dumps({}))    
                    room_info = getRoomInfo()
                    await send_action(websocket, 'R', json.dumps({'rooms': room_info}))
                    
                        

                    




    finally:
        # Remove the player from the players_no_room list when they disconnect
        print("Player disconnected")
        if websocket in players_no_room:
            players_no_room.remove(websocket)
        else: 
            players_disconnted.append(getId(websocket))

def getWordProgress(word, guessed_letters):
    return ' '.join([letter if letter in guessed_letters else '_' for letter in word])

def getUniqueLettersCount(word):
    return len(set(word))

def checkIfLetterInWord(letter, word):
    return letter in word

def getRoomInfo():
    room_info = {room: len(players['players']) for room, players in rooms.items() if rooms.get(room, {}).get('state') == 'waiting'}
    return room_info

def getNumOfPlayersInRoom(room_name):
    return len(rooms[room_name]['players'])

async def sendToHost(room_name, action, data):
    await send_action(getWebsocket(rooms[room_name]['host']), action, data)

async def send_action(websocket, action, data):
    sign = 'A'
    data = struct.pack('!BB', ord(sign), ord(action)) + json.dumps(data).encode()

    print(data)
    await websocket.send(data)

async def send_message(websocket, message):
    sign = 'M'
    data = struct.pack('!B', ord(sign)) + message.encode()
    await websocket.send(data)
    

async def sendToAllPlayersInRoomExceptHost(room_name, action, data):
    for player in rooms[room_name]['players']:
        if player != rooms[room_name]['host']:
            await send_action(getWebsocket(player), action, data)

async def sendToAllPlayersInRoom(room_name, action, data):
    for player in rooms[room_name]['players']:
        await send_action(getWebsocket(player), action, data)

async def sendToAllPlayersInRoomExcept(room_name, expect, action, data):
    for player in rooms[room_name]['players']:
        if player != expect:
            print(player)
            await send_action(getWebsocket(player), action, data)

def decode_action(buffer):
    print(buffer)
    sign, action = struct.unpack('BB', buffer[:2])
    return buffer[2:], chr(sign), chr(action)

def decode_letter(buffer):
    letter = buffer.decode('utf-8')
    return letter

def decode_roomname(buffer):
    roomnamelen = struct.unpack('B', buffer[:1])[0]
    roomname = buffer[1:1+roomnamelen].decode('utf-8')
    return roomname

def decode_index(buffer):
    index = struct.unpack('B', buffer[:1])[0]
    return index

def getWebsocket(id):
    return players_ids2websockets[id]

def getId(websocket):
    return players_websockets2ids[websocket]

# Start the WebSocket server
start_server = websockets.serve(handle_message, "localhost", 8765)

# Run the event loop
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()