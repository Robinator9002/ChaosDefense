// frontend/src/api/webSocketService.ts
import { useGameStore } from '../state/gameStore';

let websocket: WebSocket | null = null;

const connect = () => {
    // Prevent multiple connections
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        return;
    }

    const { setConnectionStatus, setInitialState, setGameTickState } = useGameStore.getState();

    const clientId = `client_${Date.now()}`;
    const wsUrl = `ws://localhost:8000/ws/${clientId}`;

    console.log('Connecting WebSocket...');
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log('WebSocket connection established.');
        setConnectionStatus(true);
    };

    websocket.onclose = () => {
        console.log('WebSocket connection closed.');
        setConnectionStatus(false);
        websocket = null; // Clear the instance on close
    };

    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus(false);
    };

    websocket.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            switch (message.type) {
                case 'initial_state':
                    setInitialState(message.data);
                    break;
                case 'game_tick':
                    setGameTickState(message.data.game_state, message.data.entities);
                    break;
                default:
                    console.warn('Received unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse incoming message:', event.data, error);
        }
    };
};

const send = (message: object) => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify(message));
    } else {
        console.error('WebSocket is not connected. Cannot send message:', message);
    }
};

export const webSocketService = {
    connect,
    send,
};
