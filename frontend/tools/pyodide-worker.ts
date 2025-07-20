import {loadPyodide, type PyodideInterface} from "pyodide";

let myLoadPyodide = (initOpts: Parameters<typeof loadPyodide>[0]) => loadPyodide({
    ...initOpts,
    stdout: (msg) => self.postMessage({stdout: msg + "\n"}), // Add newline for better readability
    stderr: (msg) => self.postMessage({stderr: msg + "\n"}), // Add newline for better readability
    stdin: () => {
        console.warn("Input requested by Python code, but stdin is not supported in this playground.");
        return "";
    },
});

let pyodideReadyPromise: Promise<PyodideInterface> | null = null;

self.onmessage = async (event: MessageEvent<any>) => {
    if (!pyodideReadyPromise) { // First message is always the init message
        // If we haven't loaded Pyodide yet, do so now.
        // This is a singleton, so we only load it once.
        pyodideReadyPromise = myLoadPyodide(event.data as Parameters<typeof loadPyodide>[0]);
        return;
    }
    // All other messages are code to run.
    let code = event.data as string;
    // make sure loading is done
    const pyodide = await pyodideReadyPromise;
    // Now load any packages we need, run the code, and send the result back.
    await pyodide.loadPackagesFromImports(code);
    try {
        self.postMessage({result: await pyodide.runPythonAsync(code)});
    } catch (error: any) {
        self.postMessage({error: error.message});
    }
};