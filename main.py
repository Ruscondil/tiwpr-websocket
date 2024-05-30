import asyncio
import websockets
import json

# List to store connected players
players_no_room = []
rooms = {}
# Function to handle incoming messages from clients
async def handle_message(websocket, path):
    players_no_room.append(websocket)
    print("Player connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get('action')

            if action == 'create_room':
                print("Room created")
                room_name = data.get('room_name')
                if room_name not in rooms:
                    rooms[room_name] = [websocket]
                    players_no_room.remove(websocket)  # Remove player from players_no_room list
                    await websocket.send(json.dumps({'message': 'Joined room info', 'room_name': room_name, 'players': 1}))
                else:
                    await websocket.send(json.dumps({'message': f'Room {room_name} already exists'})) #TODO
                room_info = {room: len(players) for room, players in rooms.items()}
                for player in players_no_room:
                    await player.send(json.dumps({'message': 'Room info', 'rooms': room_info}))

            elif action == 'get_rooms':
                room_info = {room: len(players) for room, players in rooms.items()}
                await websocket.send(json.dumps({'message': 'Room info', 'rooms': room_info}))

            elif action == 'join_room':
                room_name = data.get('room_name')
                print(f"Player joined room {room_name}")
                if room_name in rooms and len(rooms[room_name]) < 2:
                    rooms[room_name].append(websocket)
                    players_no_room.remove(websocket)
                    await rooms[room_name][0].send(json.dumps({'message': 'UpdateJoinedRoomInfo', 'players': 2}))  # Send UpdateJoinedRoomInfo message to the host
                    await rooms[room_name][1].send(json.dumps({'message': 'Joined room info', 'room_name': room_name, 'players': 2})) #TODO 2 na zmienną
                    if len(rooms[room_name]) == 2:  # If the room now has two players TODO 2 na zmienną
                        await rooms[room_name][0].send(json.dumps({'action': 'start_game'}))  # Send start_game action to the host
                else:
                    await websocket.send(json.dumps({'message': 'Room is full or does not exist'}))
    finally:
        # Remove the player from the players_no_room list when they disconnect
        if websocket in players_no_room:
            players_no_room.remove(websocket)


# Start the WebSocket server
start_server = websockets.serve(handle_message, "localhost", 8765)

# Run the event loop
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()