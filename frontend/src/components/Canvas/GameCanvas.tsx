// frontend/src/components/Canvas/GameCanvas.tsx
import { Stage, Layer, Rect, Circle } from 'react-konva';
import { useGameStore } from '../../state/gameStore';
import Konva from 'konva';

// A simple color map for different tile types. We can make this more robust later.
const tileColorMap: { [key: string]: string } = {
    BUILDABLE: '#3a5a40',
    PATH: '#582f0e',
    BORDER: '#212529',
    MOUNTAIN: '#6c757d',
    BASE_ZONE: '#023e8a',
    TOWER_OCCUPIED: '#3a5a40', // Same as buildable for now
    LAKE: '#48cae4',
    TREE: '#9ef01a',
};

const TILE_SIZE = 32; // This should eventually come from config

const GameCanvas = () => {
    // --- State Selection ---
    // FIX: Select each piece of state individually. This is the critical change
    // that prevents the infinite re-render loop. By selecting primitive values
    // or stable references, we ensure the component only re-renders when the
    // data it actually uses has changed.
    const initialState = useGameStore((state) => state.initialState);
    const entities = useGameStore((state) => state.entities);
    const selectedEntityId = useGameStore((state) => state.selectedEntityId);
    const setSelectedEntityId = useGameStore((state) => state.setSelectedEntityId);
    const clearSelections = useGameStore((state) => state.clearSelections);

    // --- Event Handlers ---
    const handleStageClick = () => {
        // When the stage (background) is clicked, clear any selections.
        clearSelections();
    };

    const handleMouseEnter = (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Change cursor to a pointer to indicate an item is clickable.
        const stage = e.target.getStage();
        if (stage) {
            stage.container().style.cursor = 'pointer';
        }
    };

    const handleMouseLeave = (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Change cursor back to default when not hovering over a clickable item.
        const stage = e.target.getStage();
        if (stage) {
            stage.container().style.cursor = 'default';
        }
    };

    // --- Render Logic ---
    // If we don't have the initial grid data, we can't render the map.
    if (!initialState) {
        return null; // Render nothing until the data is ready.
    }

    const { grid } = initialState;

    return (
        <Stage
            width={window.innerWidth}
            height={window.innerHeight}
            onClick={handleStageClick}
            onTap={handleStageClick}
        >
            {/* Layer for the static map tiles */}
            <Layer>
                {grid.tiles.map((tile) => (
                    <Rect
                        key={`${tile.x}-${tile.y}`}
                        x={tile.x * TILE_SIZE}
                        y={tile.y * TILE_SIZE}
                        width={TILE_SIZE}
                        height={TILE_SIZE}
                        fill={tileColorMap[tile.key] || '#ff00ff'} // Use a bright color for unknown tiles
                    />
                ))}
            </Layer>

            {/* Layer for all dynamic game entities (towers, enemies, etc.) */}
            <Layer>
                {/* Render Towers */}
                {entities?.towers.map((tower) => {
                    const isSelected = tower.id === selectedEntityId;
                    return (
                        <Circle
                            key={tower.id}
                            x={tower.pos.x}
                            y={tower.pos.y}
                            radius={TILE_SIZE / 2 - 4}
                            fill="#e9ecef"
                            stroke={isSelected ? '#fca311' : '#495057'} // Highlight with orange stroke if selected
                            strokeWidth={isSelected ? 4 : 2}
                            shadowColor={isSelected ? '#fca311' : undefined}
                            shadowBlur={isSelected ? 10 : 0}
                            // Stop click event from bubbling up to the stage, which would clear the selection.
                            onClick={(e) => {
                                e.cancelBubble = true;
                                setSelectedEntityId(tower.id);
                            }}
                            onTap={(e) => {
                                e.cancelBubble = true;
                                setSelectedEntityId(tower.id);
                            }}
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                        />
                    );
                })}
                {/* Render Enemies */}
                {entities?.enemies.map((enemy) => (
                    <Rect
                        key={enemy.id}
                        x={enemy.pos.x - TILE_SIZE / 2.5}
                        y={enemy.pos.y - TILE_SIZE / 2.5}
                        width={TILE_SIZE * 0.8}
                        height={TILE_SIZE * 0.8}
                        fill="#e5383b"
                        cornerRadius={4}
                    />
                ))}
            </Layer>
        </Stage>
    );
};

export default GameCanvas;
