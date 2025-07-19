// Each message needs a unique id to identify the response. In a real example,
// we might use a real uuid package
let lastId = 1;

function getId() {
    return lastId++;
}

// Add an id to msg, send it to worker, then wait for a response with the same id.
// When we get such a response, use it to resolve the promise.
function requestResponse(worker: Worker, code: String, output: (msg: string) => void) {
    return new Promise((resolve) => {
        const idWorker = getId();
        worker.addEventListener("message", function listener(event) {
            if (event.data?.stdout) {
                output(event.data.stdout + "\n");
                return;
            }
            if (event.data?.stderr) {
                output(event.data.stderr + "\n");
                return;
            }
            if (event.data?.id !== idWorker) return;
            // This listener is done so remove it.
            worker.removeEventListener("message", listener);
            // Filter the id out of the result
            const {id, ...rest} = event.data;
            resolve(rest);
        });
        worker.postMessage({id: idWorker, code});
    });
}

export function asyncRun(code: String, output: (msg: string) => void) {
    return requestResponse(pyodideWorker as Worker, code, output);
}

export function resetState() {
    // Reset the worker state by terminating it and creating a new one.
    if (pyodideWorker) pyodideWorker.terminate();
    pyodideWorker = new Worker(new URL('./pyodide-worker.ts', import.meta.url), {type: "module"});
}

export let pyodideWorker: Worker | null = null;