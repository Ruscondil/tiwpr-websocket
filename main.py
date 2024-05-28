import asyncio
import websockets

# List to store connected players
players = []

# Function to handle incoming messages from clients
async def handle_message(websocket, path):
    async for message in websocket:
        print(f"Message from client: {message}")

        # Add the player to the list of connected players
        players.append(websocket)

        # Send a message to all players with the number of connected players
        for player in players:
            await player.send(f"Number of players: {len(players)}")

        # Check if there are at least 2 players connected
        if len(players) >= 2:
            # Start the hangman game
            await start_game()

# Function to start the hangman game
async def start_game():
    # Implement your hangman game logic here
    # You can use the players list to send messages to the connected players

    # For example, you can send a message to all players to start the game
    for player in players:
        await player.send("Game started!")

# Start the WebSocket server
start_server = websockets.serve(handle_message, "localhost", 8765)

# Run the event loop
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()