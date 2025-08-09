import { app, BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url'; // Add this for __dirname
// Check if we are in development mode (Vite Dev Server) or production mode (built files)
import isDev from 'electron-is-dev';

// --- GTK Version Fix for Electron 36+ on GNOME ---
// Sets GTK version to 3 to avoid conflicts because Electron 36+
// uses GTK 4 by default on GNOME, which can cause problems
// if other parts of the app or native modules expect GTK 2/3.
// See discussion and Electron 36 release notes.
if (process.platform === 'linux') {
    // Only relevant for Linux
    app.commandLine.appendSwitch('gtk-version', '3');
}
// --- End GTK Version Fix ---

const __filename = fileURLToPath(import.meta.url); // Current file path
const __dirname = path.dirname(__filename); // Directory of the current file

function createWindow() {
    const mainWindow = new BrowserWindow({
        width: 1024,
        height: 768,
        icon: path.join(__dirname, 'public', 'narrow-icon.png'),
        webPreferences: {
            nodeIntegration: false, // Important for security, default false since Electron 5
            contextIsolation: true, // Important for security, default true since Electron 12
            // preload: path.join(__dirname, 'preload.js') // Load your preload script here if needed
        },
    });

    if (isDev) {
        // In development mode: load the URL from the Vite Dev Server
        mainWindow.loadURL('http://localhost:5173');
        // Open DevTools automatically
        mainWindow.webContents.openDevTools('detached-panel');
    } else {
        // In production mode: load the built index.html file
        mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
    }
}

// This method is called when Electron has finished initialization
// and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
    createWindow();

    app.on('activate', function () {
        // On macOS it is common to re-create a window when the dock icon is clicked
        // and there are no other open windows.
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

// Quit the app when all windows are closed, except on macOS.
// On macOS it is common for applications and their menu bar to stay active
// until the user explicitly quits with Cmd + Q.
app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        // 'darwin' means macOS
        app.quit();
    }
});

// Here you could add more main-process-specific logic.
// For example, IPC handlers for communication with the renderer process.
