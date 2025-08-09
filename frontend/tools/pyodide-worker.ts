import {loadPyodide, type PyodideAPI} from "pyodide";

let myLoadPyodide = (initOpts: Parameters<typeof loadPyodide>[0]) => loadPyodide({
    ...initOpts,
    stdout: (msg) => self.postMessage({stdout: msg + "\n"}), // Add newline for better readability
    stderr: (msg) => self.postMessage({stderr: msg + "\n"}), // Add newline for better readability
    stdin: () => {
        console.warn("Input requested by Python code, but stdin is not supported in this playground.");
        return "";
    },
});

let pyodideReadyPromise: Promise<PyodideAPI> | null = null;

export type MessageEventDataIn = {
    type: 'asyncRun';
    id: number;
    code: string;
} | {
    type: 'mkdirTree';
    id: number;
    path: string;
} | {
    type: 'writeFile';
    id: number;
    path: string;
    content: string;
} | {
    type: 'makeSnapshot';
    id: number;
}

self.onmessage = async (event: MessageEvent<MessageEventDataIn>) => {
    if (!pyodideReadyPromise) { // First message is always the init message
        // If we haven't loaded Pyodide yet, do so now.
        // This is a singleton, so we only load it once.
        pyodideReadyPromise = myLoadPyodide(event.data as Parameters<typeof loadPyodide>[0]);
        return;
    }
    if (event.data.type === 'mkdirTree') {
        // Create a directory tree in the Pyodide filesystem.
        const pyodide = await pyodideReadyPromise;
        try {
            await pyodide.FS.mkdirTree(event.data.path);
            self.postMessage({id: event.data.id, result: true});
        } catch (error: any) {
            self.postMessage({id: event.data.id, error: error.message});
        }
        return;
    } else if (event.data.type === 'writeFile') {
        // Write a file to the Pyodide filesystem.
        const pyodide = await pyodideReadyPromise;
        try {
            await pyodide.FS.writeFile(event.data.path, event.data.content);
            self.postMessage({id: event.data.id, result: true});
        } catch (error: any) {
            self.postMessage({id: event.data.id, error: error.message});
        }
    } else if (event.data.type === 'asyncRun') {
        let code = event.data.code;
        // make sure loading is done
        const pyodide = await pyodideReadyPromise;
        // Now load any packages we need, run the code, and send the result back.
        await pyodide.loadPackagesFromImports(code);
        try {
            self.postMessage({id: event.data.id, result: await pyodide.runPythonAsync(code)});
        } catch (error: any) {
            self.postMessage({id: event.data.id, error: error.message});
        }
    } else if (event.data.type === 'makeSnapshot') {
        // Take a snapshot of the current Pyodide filesystem.
        const pyodide = await pyodideReadyPromise;
        try {
            const snapshot = pyodide.makeMemorySnapshot();
            self.postMessage({id: event.data.id, result: snapshot});
        } catch (error: any) {
            self.postMessage({id: event.data.id, error: error.message});
        }
    } else {
        console.error("Unknown message type:", (event.data as any)?.type);
        self.postMessage({id: (event.data as any)?.id, error: "Unknown message type: " + (event.data as any)?.type});
    }
};