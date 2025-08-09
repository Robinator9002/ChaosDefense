// frontend/src/state/gameStore.ts
import { create } from 'zustand';
import type { InitialStateData, GameStatePayload, EntitiesPayload } from '../api/types';

// FIX: Replaced TypeScript enum with a plain object for better compatibility.
// This resolves the 'erasableSyntaxOnly' error.
export const AppScreen = {
    MainMenu: 'MainMenu',
    LevelSelect: 'LevelSelect',
    Workshop: 'Workshop',
    InGame: 'InGame',
} as const;

// Create a type from the object values for type safety.
export type AppScreenType = (typeof AppScreen)[keyof typeof AppScreen];

// --- State Interface ---
interface GameStoreState {
    // App screen state
    activeScreen: AppScreenType; // Use the new type

    // Data from the server
    initialState: InitialStateData | null;
    gameState: GameStatePayload | null;
    entities: EntitiesPayload | null;
    isConnected: boolean;

    // Client-side UI state
    selectedTowerToBuild: string | null;
    selectedEntityId: string | null;

    // Actions
    setActiveScreen: (screen: AppScreenType) => void; // Use the new type
    setConnectionStatus: (status: boolean) => void;
    setInitialState: (data: InitialStateData) => void;
    setGameTickState: (gameState: GameStatePayload, entities: EntitiesPayload) => void;
    selectTowerToBuild: (towerId: string | null) => void;
    setSelectedEntityId: (entityId: string | null) => void;
    clearSelections: () => void;
}

// --- Store Creation ---
export const useGameStore = create<GameStoreState>((set) => ({
    // --- Initial Values ---
    activeScreen: AppScreen.MainMenu, // Start on the main menu
    initialState: null,
    gameState: null,
    entities: null,
    isConnected: false,
    selectedTowerToBuild: null,
    selectedEntityId: null,

    // --- Actions Implementation ---
    setActiveScreen: (screen) => set({ activeScreen: screen }),

    setConnectionStatus: (status) => set({ isConnected: status }),

    setInitialState: (data) => set({ initialState: data }),

    setGameTickState: (gameState, entities) => set({ gameState, entities }),

    selectTowerToBuild: (towerId) =>
        set(() => {
            return { selectedTowerToBuild: towerId, selectedEntityId: null };
        }),

    setSelectedEntityId: (entityId) =>
        set((state) => {
            if (state.selectedEntityId === entityId) {
                return { selectedEntityId: null };
            }
            return { selectedEntityId: entityId, selectedTowerToBuild: null };
        }),

    clearSelections: () => set({ selectedTowerToBuild: null, selectedEntityId: null }),
}));
