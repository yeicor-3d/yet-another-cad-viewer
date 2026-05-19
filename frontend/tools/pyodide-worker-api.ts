import type { loadPyodide } from "pyodide";
import type { MessageEventDataIn } from "./pyodide-worker.ts";

let requestId = 0;

/** Simple API for the Pyodide worker. */
export function newPyodideWorker(initOpts: Parameters<typeof loadPyodide>[0]) {
  let worker = new Worker(new URL("./pyodide-worker.ts", import.meta.url), { type: "module" });
  worker.postMessage(initOpts);

  const commonRequestResponse = (event: MessageEventDataIn, stdout?: (msg: string) => void, stderr?: (msg: string) => void) => {
    return new Promise((resolve, reject) => {
      const listener = (msgEvent: MessageEvent) => {
        if (stdout && msgEvent.data?.stdout) {
          stdout(msgEvent.data.stdout);
          return;
        }
        if (stderr && msgEvent.data?.stderr) {
          stderr(msgEvent.data.stderr);
          return;
        }
        if (msgEvent.data?.id !== event.id) return;

        worker.removeEventListener("message", listener);

        if (msgEvent.data?.error) {
          reject(new Error(`Worker error: ${msgEvent.data.error}`));
        } else if (msgEvent.data?.hasOwnProperty("result")) {
          resolve(msgEvent.data.result);
        } else {
          reject(new Error("Unexpected message from worker: " + JSON.stringify(msgEvent.data)));
        }
      };

      worker.addEventListener("message", listener);

      try {
        worker.postMessage(event);
      } catch (e) {
        worker.removeEventListener("message", listener);
        reject(new Error(`Failed to post message to worker: ${e}`));
      }
    });
  };

  return {
    asyncRun: (code: string, stdout: (msg: string) => void, stderr: (msg: string) => void, version?: string, debug?: boolean, constraints?: string) =>
      commonRequestResponse({ type: "asyncRun", id: requestId++, code, version, debug, constraints }, stdout, stderr),
    mkdirTree: (path: string) => commonRequestResponse({ type: "mkdirTree", id: requestId++, path }),
    writeFile: (path: string, content: string) => commonRequestResponse({ type: "writeFile", id: requestId++, path, content }),
    makeSnapshot: () => commonRequestResponse({ type: "makeSnapshot", id: requestId++ }),
    terminate: () => {
      try {
        worker.terminate();
      } catch (e) {
        console.error("Failed to terminate worker:", e);
      }
    },
  };
}
