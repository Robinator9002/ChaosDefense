// frontend/src/components/Canvas/GameCanvas.tsx
import { Stage, Layer, Rect, Circle } from 'react-konva';
import { useGameStore } from '../../state/gameStore';
import Konva from 'konva';
import { useState, useRef, useEffect } from 'react';

// --- Constants ---
const TILE_SIZE = 32; // This should eventually come from config
const MIN_ZOOM = 0.2;
const MAX_ZOOM = 3.0;
const ZOOM_SENSITIVITY = 0.001;

// A simple color map for different tile types.
const tileColorMap: { [key: string]: string } = {
    BUILDABLE: '#3a5a40',
    PATH: '#582f0e',
    BORDER: '#212529',
    MOUNTAIN: '#6c757d',
    BASE_ZONE: '#023e8a',
    TOWER_OCCUPIED: '#3a5a40',
    LAKE: '#48cae4',
    TREE: '#9ef01a',
};

const GameCanvas = () => {
    // --- State Selection ---
    const initialState = useGameStore((state) => state.initialState);
    const entities = useGameStore((state) => state.entities);
    const selectedEntityId = useGameStore((state) => state.selectedEntityId);
    const setSelectedEntityId = useGameStore((state) => state.setSelectedEntityId);
    const clearSelections = useGameStore((state) => state.clearSelections);

    // --- Camera State ---
    const [stagePos, setStagePos] = useState({ x: 0, y: 0 });
    const [stageScale, setStageScale] = useState(1);
    const [isPanning, setIsPanning] = useState(false);
    const lastMousePos = useRef({ x: 0, y: 0 });
    const stageRef = useRef<Konva.Stage>(null);

    // --- Initial Camera Centering ---
    // This effect runs once when the component mounts and has initial data.
    // It calculates the best initial zoom and centers the map on the screen.
    useEffect(() => {
        if (initialState && stageRef.current) {
            const stage = stageRef.current;
            const { grid } = initialState;
            const mapWidth = grid.width * TILE_SIZE;
            const mapHeight = grid.height * TILE_SIZE;

            const scaleX = stage.width() / mapWidth;
            const scaleY = stage.height() / mapHeight;
            const initialScale = Math.min(scaleX, scaleY, MAX_ZOOM);
            setStageScale(initialScale);

            const initialX = (stage.width() - mapWidth * initialScale) / 2;
            const initialY = (stage.height() - mapHeight * initialScale) / 2;
            setStagePos({ x: initialX, y: initialY });
        }
    }, [initialState]);

    // --- Event Handlers ---
    const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
        e.evt.preventDefault();
        if (!stageRef.current) return;

        const stage = stageRef.current;
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();

        if (!pointer) return;

        const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale,
        };

        const delta = e.evt.deltaY;
        const newScale = Math.max(
            MIN_ZOOM,
            Math.min(oldScale - delta * ZOOM_SENSITIVITY, MAX_ZOOM),
        );

        setStageScale(newScale);
        const newPos = {
            x: pointer.x - mousePointTo.x * newScale,
            y: pointer.y - mousePointTo.y * newScale,
        };
        setStagePos(newPos);
    };

    const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Middle mouse button for panning
        if (e.evt.button === 1) {
            setIsPanning(true);
            lastMousePos.current = { x: e.evt.clientX, y: e.evt.clientY };
            e.evt.preventDefault();
        }
    };

    const handleMouseUp = (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (e.evt.button === 1) {
            setIsPanning(false);
        }
    };

    const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (isPanning) {
            const newMousePos = { x: e.evt.clientX, y: e.evt.clientY };
            const dx = newMousePos.x - lastMousePos.current.x;
            const dy = newMousePos.y - lastMousePos.current.y;
            lastMousePos.current = newMousePos;
            setStagePos((prevPos) => ({ x: prevPos.x + dx, y: prevPos.y + dy }));
        }
    };

    const handleStageClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Clear selections only if the click was on the stage itself
        if (e.target === e.target.getStage()) {
            clearSelections();
        }
    };

    // --- Render Logic ---
    if (!initialState) {
        return null;
    }

    const { grid } = initialState;

    return (
        <Stage
            ref={stageRef}
            width={window.innerWidth}
            height={window.innerHeight}
            x={stagePos.x}
            y={stagePos.y}
            scaleX={stageScale}
            scaleY={stageScale}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseMove={handleMouseMove}
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
                        fill={tileColorMap[tile.key] || '#ff00ff'}
                    />
                ))}
            </Layer>

            {/* Layer for all dynamic game entities */}
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
                            stroke={isSelected ? '#fca311' : '#495057'}
                            strokeWidth={isSelected ? 4 / stageScale : 2 / stageScale}
                            shadowColor={isSelected ? '#fca311' : undefined}
                            shadowBlur={isSelected ? 10 : 0}
                            onClick={(e) => {
                                e.cancelBubble = true;
                                setSelectedEntityId(tower.id);
                            }}
                            onTap={(e) => {
                                e.cancelBubble = true;
                                setSelectedEntityId(tower.id);
                            }}
                        />
                    );
                })}
                {/* Render Enemies */}
                {entities?.enemies.map((enemy) => (
                    <Rect
                        key={enemy.id}
                        x={enemy.pos.x - TILE_SIZE * 0.4}
                        y={enemy.pos.y - TILE_SIZE * 0.4}
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
