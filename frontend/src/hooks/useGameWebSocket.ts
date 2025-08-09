// frontend/src/hooks/useGameWebSocket.ts
import { useEffect, useRef } from 'react';
import { useGameStore } from '../state/gameStore';

/**
 * A custom React hook to manage the WebSocket connection and update the global game store.
 * This hook is the single point of communication with the backend server.
 */
export const useGameWebSocket = () => {
    // Get the state-updating actions from our Zustand store.
    const { setConnectionStatus, setInitialState, setGameTickState } = useGameStore();
    // useRef holds the WebSocket instance without causing re-renders.
    const websocket = useRef<WebSocket | null>(null);

    // This useEffect hook runs once when the hook is first used,
    // establishing the connection.
    useEffect(() => {
        // Prevent creating multiple connections if the hook re-renders for some reason.
        if (websocket.current) return;

        const clientId = `client_${Date.now()}`;
        const wsUrl = `ws://localhost:8000/ws/${clientId}`;

        console.log('Attempting to connect to WebSocket...');
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connection established.');
            // Update the global store with the connection status.
            setConnectionStatus(true);
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed.');
            setConnectionStatus(false);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            setConnectionStatus(false);
        };

        // This is the core message handler. It listens for messages and updates the store.
        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                switch (message.type) {
                    case 'initial_state':
                        console.log('Received initial state, updating store...');
                        setInitialState(message.data);
                        break;
                    case 'game_tick':
                        // For game ticks, we update the dynamic parts of the state.
                        setGameTickState(message.data.game_state, message.data.entities);
                        break;
                    default:
                        console.warn('Received unknown message type:', message.type);
                }
            } catch (error) {
                console.error('Failed to parse incoming message:', event.data, error);
            }
        };

        websocket.current = ws;

        // The cleanup function is critical. It runs when the component using the hook
        // unmounts, ensuring we close the connection gracefully.
        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                console.log('Closing WebSocket connection.');
                ws.close();
            }
        };
        // The dependency array is empty, so this effect runs only once.
    }, [setConnectionStatus, setInitialState, setGameTickState]);

    // The hook itself doesn't need to return anything, as it communicates
    // with the rest of the app via the global store.
};
