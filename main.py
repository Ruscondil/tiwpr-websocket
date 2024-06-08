import asyncio
import websockets
import json
import random

# List to store connected players
players_no_room = []
rooms = {}
players_in_rooms = {}

max_players_in_room = 2

possible_words = ['gustaw','miau','test']

# Function to handle incoming messages from clients
async def handle_message(websocket, path):
    players_no_room.append(websocket)
    print("Player connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get('action')
            if players_in_rooms.get(websocket) is None:
                if action == 'create_room':
                    print("Room created")
                    room_name = data.get('room_name')
                    if room_name not in rooms:
                        rooms[room_name] = {'players': [], 'state': 'waiting', 'word': '', 'word_length': 0, 'guessed_letters': []}
                        rooms[room_name]['players'].append(websocket)
                        players_in_rooms[websocket] = room_name
                        players_no_room.remove(websocket)  # Remove player from players_no_room list
                        await websocket.send(json.dumps({'message': 'Joined_RoomInfo', 'room_name': room_name, 'players': 1, 'max_players': max_players_in_room}))
                    else:
                        await websocket.send(json.dumps({'message': f'Room {room_name} already exists'})) #TODO
                    room_info = getRoomInfo()
                    for player in players_no_room:
                        await player.send(json.dumps({'message': 'Room info', 'rooms': room_info}))
                
                elif action == 'get_rooms':
                    room_info = getRoomInfo()
                    await websocket.send(json.dumps({'message': 'Room info', 'rooms': room_info}))

                elif action == 'join_room':
                    room_name = data.get('room_name')
                    print(f"Player joined room {room_name}")
                    if room_name in rooms and len(rooms[room_name]['players']) < max_players_in_room:
                        rooms[room_name]['players'].append(websocket)
                        players_in_rooms[websocket] = room_name
                        players_no_room.remove(websocket)
                        await rooms[room_name]['players'][0].send(json.dumps({'message': 'UpdateJoinedRoomInfo', 'players': getNumOfPlayersInRoom(room_name), 'max_players': max_players_in_room}))  # Send UpdateJoinedRoomInfo message to the host
                        await rooms[room_name]['players'][1].send(json.dumps({'message': 'Joined_RoomInfo', 'room_name': room_name, 'players': getNumOfPlayersInRoom(room_name), 'max_players': max_players_in_room})) 
                        if getNumOfPlayersInRoom(room_name) == max_players_in_room:  # If the room now has two players 
                            await rooms[room_name]['players'][0].send(json.dumps({'action': 'can_start_game'}))  # Send start_game action to the host
                    else:
                        await websocket.send(json.dumps({'message': 'Room is full or does not exist'}))
            elif players_in_rooms[websocket] and rooms[players_in_rooms[websocket]]['state'] == 'waiting':
                if action == 'start_game':
                    print("Game started")
               
                    rooms[room_name]["state"] = "playing"
                    rooms[room_name]["word"] = random.choice(possible_words)
                    rooms[room_name]["word_length"] = len(rooms[room_name]["word"])
                    rooms[room_name]["guessed_letters"] = []
                    print("Word: ", rooms[room_name]["word"])

                    for player in rooms[room_name]['players']:
                        await player.send(json.dumps({'action': 'StartGame', 'word_length': rooms[room_name]["word_length"], 'wordProgress': getWordProgress(rooms[room_name]["word"], rooms[room_name]["guessed_letters"])}))
            elif players_in_rooms[websocket] and rooms[players_in_rooms[websocket]]['state'] == 'playing':
                if action == 'guess_letter':
                    letter = data.get('letter')
                    print("Guess letter", letter)
                    guessed_letters = rooms[room_name]['guessed_letters']
                    word = rooms[room_name]['word']

                    if len(letter) == 1 and letter.isalpha():
                        if letter not in guessed_letters:
                            guessed_letters.append(letter)
                            wordProgress = getWordProgress(word, guessed_letters)
                            if wordProgress == word:
                                await rooms[room_name]['players'][0].send(json.dumps({'action': 'game_over', 'winner': 0}))
                                await rooms[room_name]['players'][1].send(json.dumps({'action': 'game_over', 'winner': 1}))
                            else:
                                for player in rooms[room_name]['players']:
                                    await player.send(json.dumps({'action': 'UpdateWordProgress', 'wordProgress': wordProgress}))
                        else:
                            await websocket.send(json.dumps({'message': 'Letter already guessed'})) #TODO
                    else:
                        await websocket.send(json.dumps({'message': 'Invalid letter'})) #TODO



    finally:
        # Remove the player from the players_no_room list when they disconnect
        if websocket in players_no_room:
            players_no_room.remove(websocket)

def getWordProgress(word, guessed_letters):
    return ' '.join([letter if letter in guessed_letters else '_' for letter in word])

def getRoomInfo():
    room_info = {room: len(players['players']) for room, players in rooms.items()}
    return room_info

def getNumOfPlayersInRoom(room_name):
    return len(rooms[room_name]['players'])
# Start the WebSocket server
start_server = websockets.serve(handle_message, "localhost", 8765)

# Run the event loop
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()