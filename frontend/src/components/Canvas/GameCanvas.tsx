// frontend/src/components/Canvas/GameCanvas.tsx
import { Stage, Layer, Rect, Circle } from 'react-konva';
import type { InitialStateData, EntitiesPayload } from '../../api/types'; // We'll move types to a dedicated file soon

interface GameCanvasProps {
    initialState: InitialStateData | null;
    entities: EntitiesPayload | null;
}

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

const GameCanvas = ({ initialState, entities }: GameCanvasProps) => {
    if (!initialState) {
        // If we don't have the initial state yet, we can't render the map.
        return (
            <div className="w-full h-full bg-black flex items-center justify-center">
                <p>Loading Map...</p>
            </div>
        );
    }

    const { grid } = initialState;

    return (
        <Stage width={window.innerWidth} height={window.innerHeight}>
            {/* Layer for the static map grid */}
            <Layer>
                {grid.tiles.map((tile) => (
                    <Rect
                        key={`${tile.x}-${tile.y}`}
                        x={tile.x * TILE_SIZE}
                        y={tile.y * TILE_SIZE}
                        width={TILE_SIZE}
                        height={TILE_SIZE}
                        fill={tileColorMap[tile.key] || '#ff00ff'} // Default to magenta for unknown tiles
                    />
                ))}
            </Layer>

            {/* Layer for dynamic entities (towers, enemies, etc.) */}
            <Layer>
                {entities?.towers.map((tower) => (
                    <Circle
                        key={tower.id}
                        x={tower.pos.x}
                        y={tower.pos.y}
                        radius={TILE_SIZE / 2 - 4}
                        fill="#e9ecef"
                        stroke="#495057"
                        strokeWidth={2}
                    />
                ))}
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
