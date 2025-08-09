// frontend/src/App.tsx
import { useState, useEffect, useRef } from 'react';

// --- Type Definitions ---
// It's crucial to define the 'shape' of the data we expect from the backend.
// This gives us type safety and autocompletion. These types are based on our
// Python serialization functions.

interface Vector2 {
    x: number;
    y: number;
}

interface GameEntity {
    id: string;
    type_id: string;
    pos: Vector2;
    is_alive: boolean;
}

interface Enemy extends GameEntity {
    hp: number;
    max_hp: number;
}

interface Tower extends GameEntity {
    range: number;
}

interface Projectile extends GameEntity {}

interface GameStatePayload {
    gold: number;
    base_hp: number;
    wave: number;
    game_over: boolean;
    victory: boolean;
}

interface EntitiesPayload {
    towers: Tower[];
    enemies: Enemy[];
    projectiles: Projectile[];
}

interface InitialStateData {
    // TODO: Define types for grid, paths, and buildable towers
}

// --- Main App Component ---

function App() {
    // --- State Management ---
    // We use React's state hooks to store the data received from the WebSocket.
    // When this state changes, React will automatically re-render the components.
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [gameState, setGameState] = useState<GameStatePayload | null>(null);
    const [entities, setEntities] = useState<EntitiesPayload | null>(null);
    const [initialState, setInitialState] = useState<InitialStateData | null>(null);

    // useRef is used to hold a persistent reference to the WebSocket object
    // without causing re-renders when it's set.
    const websocket = useRef<WebSocket | null>(null);

    // --- WebSocket Connection Logic ---
    useEffect(() => {
        // This effect runs once when the component mounts.
        // It's the perfect place to establish our WebSocket connection.

        // A unique ID for this client session.
        const clientId = `client_${Date.now()}`;
        const wsUrl = `ws://localhost:8000/ws/${clientId}`; // Assumes backend runs on port 8000

        console.log('Attempting to connect to WebSocket...');
        websocket.current = new WebSocket(wsUrl);

        websocket.current.onopen = () => {
            console.log('WebSocket connection established.');
            setIsConnected(true);
        };

        websocket.current.onclose = () => {
            console.log('WebSocket connection closed.');
            setIsConnected(false);
        };

        websocket.current.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        // This is the core message handler. It listens for messages from the backend.
        websocket.current.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                // We check the 'type' field to determine how to handle the data.
                switch (message.type) {
                    case 'initial_state':
                        console.log('Received initial state:', message.data);
                        setInitialState(message.data);
                        break;
                    case 'game_tick':
                        // For game ticks, we update the dynamic parts of the state.
                        setGameState(message.data.game_state);
                        setEntities(message.data.entities);
                        break;
                    // TODO: Add cases for 'game_over', etc.
                    default:
                        console.warn('Received unknown message type:', message.type);
                }
            } catch (error) {
                console.error('Failed to parse incoming message:', event.data, error);
            }
        };

        // Cleanup function: This is called when the component unmounts.
        // It's essential for closing the connection gracefully.
        return () => {
            if (websocket.current) {
                console.log('Closing WebSocket connection.');
                websocket.current.close();
            }
        };
    }, []); // The empty dependency array means this effect runs only once.

    // --- Rendering Logic ---
    // This is a simple placeholder for now. In the next steps, we will build
    // out the actual UI components and render them here based on the game state.
    return (
        <div className="bg-gray-900 text-white w-screen h-screen flex flex-col items-center justify-center font-mono">
            <h1 className="text-4xl font-bold mb-4">ChaosDefense - React Frontend</h1>
            <div className="p-4 border rounded-lg bg-gray-800 shadow-lg">
                <p className="mb-2">
                    Connection Status:{' '}
                    <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
                        {isConnected ? 'Connected' : 'Disconnected'}
                    </span>
                </p>
                {gameState && (
                    <div>
                        <p>
                            Gold: <span className="text-yellow-400">{gameState.gold}</span>
                        </p>
                        <p>
                            HP: <span className="text-red-500">{gameState.base_hp}</span>
                        </p>
                        <p>
                            Wave: <span className="text-blue-400">{gameState.wave}</span>
                        </p>
                    </div>
                )}
                {entities && (
                    <div className="mt-4 text-xs">
                        <p>Towers: {entities.towers.length}</p>
                        <p>Enemies: {entities.enemies.length}</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
