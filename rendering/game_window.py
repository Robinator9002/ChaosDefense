# rendering/game_window.py
from __future__ import annotations
import arcade
import logging
from pathlib import Path

# Importiert die notwendigen Klassen aus deinen anderen Projektdateien.
# Diese Struktur sorgt für eine saubere Trennung der Zuständigkeiten.
from game_logic.game_state import GameState
from level_generation.grid import Grid
from level_generation.generator import LevelGenerator
from rendering.sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# Konstanten für die Steuerung
SCROLL_SPEED = 1.0  # Beeinflusst, wie schnell die Karte mit der Maus verschoben wird
MIN_ZOOM = 0.3  # Wie weit man herauszoomen kann
MAX_ZOOM = 2.5  # Wie weit man hineinzoomen kann
ZOOM_INCREMENT = 0.1  # Wie stark eine einzelne Mausrad-Bewegung den Zoom ändert


class GameWindow(arcade.Window):
    """
    Das Hauptfenster des Spiels. Diese Klasse ist der Dreh- und Angelpunkt für
    das Rendering, die Annahme von Benutzereingaben und die Orchestrierung
    der Haupt-Spielelemente.
    """

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        game_settings: dict,
        level_styles: dict,
        assets_path: Path,
    ):
        """
        Initialisiert das Fenster und bereitet die Spiel-Subsysteme vor.

        Args:
            width (int): Fensterbreite
            height (int): Fensterhöhe
            title (str): Fenstertitel
            game_settings (dict): Geladene Konfiguration aus game_settings.json
            level_styles (dict): Geladene Konfiguration aus level_styles.json
            assets_path (Path): Pfad zum 'assets'-Verzeichnis
        """
        super().__init__(width, height, title, resizable=True)

        # Speichert die Konfigurationen und Pfade für späteren Gebrauch
        self.game_settings = game_settings
        self.level_styles = level_styles
        self.assets_path = assets_path

        # Initialisiert die Hauptkomponenten des Spiels.
        # Diese werden in der setup()-Methode mit konkreten Objekten befüllt.
        self.game_state: GameState | None = None
        self.grid: Grid | None = None
        self.sprite_renderer: SpriteRenderer | None = None

        # --- Kamera-Setup ---
        # Wir verwenden zwei Kameras:
        # 1. scene_camera: Für die Spielwelt (Karte, Türme, Gegner). Diese wird bewegt und gezoomt.
        # 2. gui_camera: Für die Benutzeroberfläche (HUD). Diese bleibt immer statisch.
        self.scene_camera = arcade.Camera(width, height)
        self.gui_camera = arcade.Camera(width, height)

        # --- Steuerungs-Variablen ---
        # Für das Verschieben der Karte mit der Maus
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.camera_start_x = 0
        self.camera_start_y = 0

    def setup(self):
        """
        Setzt das Spiel auf. Wird einmal zu Beginn aufgerufen, um alle
        notwendigen Objekte zu erstellen und zu initialisieren.
        """
        logger.info("--- Starting Game Setup ---")

        # 1. Spielzustand initialisieren
        self.game_state = GameState(gold=150, base_hp=20)

        # 2. Logisches Grid für die Karte erstellen
        grid_width = self.game_settings.get("grid_width", 40)
        grid_height = self.game_settings.get("grid_height", 22)
        self.grid = Grid(grid_width, grid_height)

        # 3. Level prozedural generieren
        # LevelGenerator modifiziert das Grid-Objekt direkt.
        LevelGenerator.generate(self.grid)
        self.game_state.level_grid = self.grid  # Den Grid im GameState speichern

        # 4. Level-Stil auswählen und Hintergrund setzen
        # Hier wird "Forest" fest einprogrammiert, könnte aber später wählbar sein.
        current_style = self.level_styles.get("Forest", {})
        style_definitions = current_style.get("tile_definitions", {})
        bg_color = current_style.get("background_color", (0, 0, 0))
        self.background_color = bg_color

        # 5. SpriteRenderer erstellen, der das Grid in Sprites umwandelt
        tile_size = self.game_settings.get("tile_size", 32)
        self.sprite_renderer = SpriteRenderer(
            grid=self.grid,
            tile_size=tile_size,
            style_definitions=style_definitions,
            assets_path=self.assets_path,
        )

        # Zentriert die Kamera initial auf der Mitte der Karte
        map_center_x = self.grid.width * tile_size / 2
        map_center_y = self.grid.height * tile_size / 2
        self.center_camera_on_point(map_center_x, map_center_y)

        logger.info("--- Game Setup Complete ---")

    def on_draw(self):
        """
        Die Haupt-Zeichenroutine. Wird von Arcade kontinuierlich aufgerufen.
        """
        self.clear()

        # --- Spielwelt zeichnen ---
        # Aktiviert die Kamera für die Szene. Alle nachfolgenden Zeichenbefehle
        # werden durch diese Kamera transformiert (verschoben, gezoomt).
        self.scene_camera.use()
        if self.sprite_renderer:
            self.sprite_renderer.draw()
        # Hier würden später auch Türme, Gegner, Projektile etc. gezeichnet.

        # --- GUI / HUD zeichnen ---
        # Aktiviert die Kamera für die Benutzeroberfläche. Diese ist statisch.
        self.gui_camera.use()
        self.draw_gui()

    def draw_gui(self):
        """Zeichnet alle Elemente der Benutzeroberfläche."""
        if not self.game_state:
            return

        # Zeichnet einen halbtransparenten Kasten als Hintergrund für den Text,
        # damit er immer gut lesbar ist.
        arcade.draw_rectangle_filled(
            center_x=120,
            center_y=self.height - 40,
            width=220,
            height=70,
            color=(0, 0, 0, 150),  # Schwarz mit 150/255 Deckkraft
        )

        # Holt die aktuellen Werte aus dem GameState und zeigt sie an.
        gold_text = f"Gold: {self.game_state.gold}"
        hp_text = f"Base HP: {self.game_state.base_hp}"
        wave_text = f"Wave: {self.game_state.current_wave_number}"

        arcade.draw_text(gold_text, 15, self.height - 30, arcade.color.GOLD, 16)
        arcade.draw_text(hp_text, 15, self.height - 55, arcade.color.RED, 16)
        arcade.draw_text(wave_text, 15, self.height - 80, arcade.color.CYAN, 16)

    def center_camera_on_point(self, x, y):
        """Zentriert die scene_camera auf einen bestimmten Punkt in der Spielwelt."""
        self.scene_camera.move_to((x - self.width / 2, y - self.height / 2))

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """Wird aufgerufen, wenn eine Maustaste gedrückt wird."""
        # Mittlere Maustaste für das Verschieben der Karte (Panning)
        if button == arcade.MOUSE_BUTTON_MIDDLE:
            self.is_panning = True
            self.pan_start_x = x
            self.pan_start_y = y
            # Speichert die Kameraposition beim Start des Verschiebens
            self.camera_start_x, self.camera_start_y = self.scene_camera.position

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        """Wird aufgerufen, wenn eine Maustaste losgelassen wird."""
        if button == arcade.MOUSE_BUTTON_MIDDLE:
            self.is_panning = False

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        """Wird aufgerufen, wenn die Maus bewegt wird."""
        if self.is_panning:
            # Berechnet die Verschiebung der Maus seit dem Klick
            delta_x = x - self.pan_start_x
            delta_y = y - self.pan_start_y

            # Die Verschiebung muss durch den Zoomfaktor geteilt werden,
            # damit die Karte sich "natürlich" unter dem Mauszeiger bewegt.
            # Die Bewegung wird invertiert (-delta), da die Kamera in die
            # entgegengesetzte Richtung der Mausbewegung ziehen muss.
            cam_x = self.camera_start_x - delta_x / self.scene_camera.zoom
            cam_y = self.camera_start_y - delta_y / self.scene_camera.zoom

            self.scene_camera.move_to((cam_x, cam_y))

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        """Wird aufgerufen, wenn das Mausrad gescrollt wird, um zu zoomen."""
        # Berechnet den neuen Zoom-Faktor
        zoom_amount = 1 + (scroll_y * ZOOM_INCREMENT)
        new_zoom = self.scene_camera.zoom * zoom_amount

        # Begrenzt den Zoom auf die definierten Min/Max-Werte
        self.scene_camera.zoom = max(MIN_ZOOM, min(new_zoom, MAX_ZOOM))

    def on_update(self, delta_time: float):
        """
        Wird für jeden Frame aufgerufen. Hier findet die Spiellogik statt.
        (z.B. Gegner bewegen, Türme schießen lassen)
        """
        # Momentan leer, wird aber für die zukünftige Logik benötigt.
        pass

    def on_resize(self, width: int, height: int):
        """Wird aufgerufen, wenn die Fenstergröße geändert wird."""
        super().on_resize(width, height)
        # Passt die Kameras an die neue Fenstergröße an
        self.scene_camera.resize(width, height)
        self.gui_camera.resize(width, height)
        logger.info(f"Window resized to: {width}x{height}")
