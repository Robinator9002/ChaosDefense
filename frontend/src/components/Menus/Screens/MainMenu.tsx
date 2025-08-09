// frontend/src/components/Menus/Screens/MainMenu.tsx
import { useGameStore, AppScreen } from '../../../state/gameStore';

const MainMenu = () => {
    // Get the action to change the screen from our global store.
    const setActiveScreen = useGameStore((state) => state.setActiveScreen);

    const handlePlayClick = () => {
        // For now, clicking Play will jump directly into the game.
        // Later, this will change to AppScreen.LevelSelect.
        setActiveScreen(AppScreen.InGame);
    };

    return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900">
            <h1 className="text-7xl font-bold text-white mb-4 tracking-wider">ChaosDefense</h1>
            <p className="text-gray-400 mb-16">A React & Python Tower Defense Game</p>

            <div className="flex flex-col gap-6 w-72">
                <button
                    onClick={handlePlayClick}
                    className="px-8 py-4 bg-blue-600 text-white text-xl font-bold rounded-lg shadow-lg hover:bg-blue-700 transition-all duration-200 transform hover:scale-105"
                >
                    Play
                </button>
                <button
                    // onClick={() => setActiveScreen(AppScreen.Workshop)}
                    className="px-8 py-4 bg-gray-700 text-gray-400 text-xl font-bold rounded-lg shadow-lg hover:bg-gray-600 hover:text-white transition-all duration-200 cursor-not-allowed"
                    disabled
                >
                    The Workshop
                </button>
                <button
                    // onClick={() => { /* Logic for quitting Electron app */ }}
                    className="px-8 py-4 bg-gray-700 text-gray-400 text-xl font-bold rounded-lg shadow-lg hover:bg-gray-600 hover:text-white transition-all duration-200 cursor-not-allowed"
                    disabled
                >
                    Quit
                </button>
            </div>
        </div>
    );
};

export default MainMenu;
