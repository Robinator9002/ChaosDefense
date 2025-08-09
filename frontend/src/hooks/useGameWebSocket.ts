// frontend/src/hooks/useGameWebSocket.ts
import { useEffect } from 'react';
import { webSocketService } from '../api/webSocketService';

/**
 * A custom React hook that ensures the WebSocket connection is established
 * when the application loads.
 */
export const useGameWebSocket = () => {
    useEffect(() => {
        // Connect on component mount
        webSocketService.connect();

        // The service itself handles cleanup, so we don't need to return anything here.
    }, []); // Empty dependency array ensures this runs only once.
};
