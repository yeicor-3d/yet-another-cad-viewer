import type {loadPyodide} from "pyodide";

/** Simple API for the Pyodide worker. */
export function newPyodideWorker(initOpts: Parameters<typeof loadPyodide>[0]) {
    let worker = new Worker(new URL('./pyodide-worker.ts', import.meta.url), {type: "module"});
    worker.postMessage(initOpts);
    return {
        asyncRun: (code: String, stdout: (msg: string) => void, stderr: (msg: string) => void) => new Promise((resolve, reject) => {
            worker.addEventListener("message", function listener(event) {
                if (event.data?.stdout) {
                    stdout(event.data.stdout);
                    return;
                }
                if (event.data?.stderr) {
                    stderr(event.data.stderr);
                    return;
                }
                // Result or error.
                worker.removeEventListener("message", listener);
                if (event.data?.error) {
                    reject(event.data.error);
                } else {
                    resolve(event.data?.result);
                }
            });
            worker.postMessage(code);
        }),
        terminate: () => worker.terminate()
    }
}

