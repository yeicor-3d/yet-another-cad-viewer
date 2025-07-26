import type {loadPyodide} from "pyodide";
import type {MessageEventDataIn} from "./pyodide-worker.ts";

let requestId = 0;

/** Simple API for the Pyodide worker. */
export function newPyodideWorker(initOpts: Parameters<typeof loadPyodide>[0]) {
    let worker = new Worker(new URL('./pyodide-worker.ts', import.meta.url), {type: "module"});
    worker.postMessage(initOpts);
    const commonRequestResponse = (event: MessageEventDataIn, stdout?: (msg: string) => void, stderr?: (msg: string) => void) => {
        return new Promise((resolve, reject) => {
            worker.addEventListener("message", function listener(event: MessageEvent) {
                if (stdout && event.data?.stdout) {
                    stdout(event.data.stdout); // No clue if associated with this request, but we handle it anyway.
                    return;
                }
                if (stderr && event.data?.stderr) {
                    stderr(event.data.stderr); // No clue if associated with this request, but we handle it anyway.
                    return;
                }
                if (event.data?.id !== event.data.id) return; // Ignore messages that are not for this request.
                if (event.data?.error) {
                    worker.removeEventListener("message", listener);
                    reject(event.data.error);
                } else if (event.data?.hasOwnProperty("result")) {
                    worker.removeEventListener("message", listener);
                    resolve(event.data.result);
                } else {
                    throw new Error("Unexpected message from worker: " + JSON.stringify(event.data));
                }
            })
            worker.postMessage(event);
        });
    }
    return {
        asyncRun: (code: string, stdout: (msg: string) => void, stderr: (msg: string) => void) =>
            commonRequestResponse({type: "asyncRun", id: requestId++, code}, stdout, stderr),
        mkdirTree: (path: string) => commonRequestResponse({type: "mkdirTree", id: requestId++, path}),
        writeFile: (path: string, content: string) =>
            commonRequestResponse({type: "writeFile", id: requestId++, path, content}),
        makeSnapshot: () => commonRequestResponse({type: "makeSnapshot", id: requestId++}),
        terminate: () => worker.terminate()
    }
}

