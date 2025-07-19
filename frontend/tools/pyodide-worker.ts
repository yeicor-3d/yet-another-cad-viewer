import {loadPyodide, version} from "pyodide";

let pyodideReadyPromise = loadPyodide({
    indexURL: `https://cdn.jsdelivr.net/pyodide/v${version}/full/`, // FIXME: Local deployment?
    packages: ["micropip", "sqlite3"], // Preloaded faster here...
    stdout: (msg) => self.postMessage({stdout: msg}),
    stderr: (msg) => self.postMessage({stderr: msg}),
    stdin: () => {
        console.warn("Input requested by Python code, but stdin is not supported in this playground.");
        return "";
    },
});

self.onmessage = async (event) => {
    // make sure loading is done
    const pyodide = await pyodideReadyPromise;
    const {id, code} = event.data;
    // Now load any packages we need, run the code, and send the result back.
    await pyodide.loadPackagesFromImports(code);
    try {
        // Execute the python code in this context
        const result = await pyodide.runPythonAsync(code);
        self.postMessage({result, id});
    } catch (error: any) {
        self.postMessage({error: error.message, id});
    }
};