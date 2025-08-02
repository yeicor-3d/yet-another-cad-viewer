import {settings} from "./settings";

const batchTimeout = 250; // ms

export class NetworkUpdateEventModel {
    name: string;
    url: string | Blob;
    // TODO: Detect and manage instances of the same object (same hash, different name)
    hash: string | null;
    isRemove: boolean | null; // This is null for a shutdown event

    constructor(name: string, url: string | Blob, hash: string | null, isRemove: boolean | null) {
        this.name = name;
        this.url = url;
        this.hash = hash;
        this.isRemove = isRemove;
    }
}

export class NetworkUpdateEvent extends Event {
    models: NetworkUpdateEventModel[];
    disconnect: () => void;

    constructor(models: NetworkUpdateEventModel[], disconnect: () => void) {
        super("update");
        this.models = models;
        this.disconnect = disconnect;
    }
}

/** Listens for updates and emits events when a model changes */
export class NetworkManager extends EventTarget {
    private knownObjectHashes: { [name: string]: string | null } = {};
    private bufferedUpdates: NetworkUpdateEventModel[] = [];
    private batchTimeout: number | null = null;

    /**
     * Tries to load a new model (.glb) from the given URL.
     *
     * If the URL uses the websocket protocol (ws:// or wss://), the server will be continuously monitored for changes.
     * In this case, it will only trigger updates if the name or hash of any model changes.
     *
     * Updates will be emitted as "update" events, including the download URL and the model name.
     */
    async load(url: string | Blob) {
        if (!(url instanceof Blob) && (url.startsWith("dev+") || url.startsWith("dev "))) {
            let baseUrl = new URL(url.slice(4));
            baseUrl.searchParams.set("api_updates", "true");
            await this.monitorDevServer(baseUrl);
        } else {
            let name;
            let hash = null;
            if (url instanceof Blob) {
                if (url instanceof File) name = (url as File).name
                else name = `blob-${Math.random()}`;
                name = name.replace('.glb', '').replace('.gltf', '');
            } else {
                // If there is a #name parameter in the URL, use it as the name
                let hashParams: URLSearchParams
                try {
                    let urlObj = new URL(url, window.location.href);
                    hashParams = new URLSearchParams(urlObj.hash.slice(1));
                } catch (e) {
                    hashParams = new URLSearchParams();
                }
                if (hashParams.has("name")) {
                    name = hashParams.get("name") || `unknown-${Math.random()}`;
                } else { // Default to the last part of the URL as the "name" of the model
                    name = url.split("/").pop();
                }
                name = name?.split(".")[0] || `unknown-${Math.random()}`;
                // Use a head request to get the hash of the file
                let response = await fetch(url, {method: "HEAD"});
                hash = response.headers.get("etag");
            }
            // Only trigger an update if the hash has changed
            this.foundModel(name, hash, url, false);
        }
    }

    private async monitorDevServer(url: URL, stop: () => boolean = () => false) {
        while (!stop()) {
            let monitorEveryMs = (await settings).monitorEveryMs;
            try {
                // WARNING: This will spam the console logs with failed requests when the server is down
                const controller = new AbortController();
                let response = await fetch(url.toString(), {signal: controller.signal});
                // console.log("Monitoring", url.toString(), response);
                if (response.status === 200) {
                    let lines = readLinesStreamings(response.body!.getReader());
                    for await (let line of lines) {
                        if (stop()) break;
                        if (!line || !line.startsWith("data:")) continue;
                        let data: { name: string, hash: string, is_remove: boolean | null } = JSON.parse(line.slice(5));
                        // console.debug("WebSocket message", data);
                        let urlObj = new URL(url);
                        urlObj.searchParams.delete("api_updates");
                        urlObj.searchParams.set("api_object", data.name);
                        this.foundModel(data.name, data.hash, urlObj.toString(), data.is_remove, async () => {
                            controller.abort(); // Notify the server that we are done
                        });
                    }
                } else {
                    // Server is down, wait a little longer before retrying
                    await new Promise(resolve => setTimeout(resolve, 10 * monitorEveryMs));
                }
                controller.abort();
            } catch (e) { // Ignore errors (retry very soon)
            }
            await new Promise(resolve => setTimeout(resolve, monitorEveryMs));
        }
    }

    private foundModel(name: string, hash: string | null, url: string | Blob, isRemove: boolean | null, disconnect: () => void = () => {
    }) {
        // console.debug("Found model", name, "with hash", hash, "at", url, "isRemove", isRemove);

        // We only care about the latest update per model name
        this.bufferedUpdates = this.bufferedUpdates.filter(m => m.name !== name);

        // Add the new model to the list of updates and dispatch the early update
        let upd = new NetworkUpdateEventModel(name, url, hash, isRemove);
        this.bufferedUpdates.push(upd);
        this.dispatchEvent(new CustomEvent("update-early", {detail: this.bufferedUpdates}));

        // Optimization: try to batch updates automatically for faster rendering
        if (this.batchTimeout !== null) clearTimeout(this.batchTimeout);
        this.batchTimeout = setTimeout(() => {
            // Update known hashes for minimal updates
            for (let model of this.bufferedUpdates) {
                if (model.isRemove == false && model.hash && model.hash === this.knownObjectHashes[model.name]) {
                    // Delete this useless update
                    let foundFirst = false;
                    this.bufferedUpdates = this.bufferedUpdates.filter(m => {
                        if (m === model) {
                            if (!foundFirst) { // Remove only first full match
                                foundFirst = true;
                                return false;
                            }
                        }
                        return true;
                    })
                } else {
                    // Keep this update and update the last known hash
                    if (model.isRemove == true) {
                        if (model.name in this.knownObjectHashes) delete this.knownObjectHashes[model.name];
                    } else if (model.isRemove == false) {
                        this.knownObjectHashes[model.name] = model.hash;
                    }
                }
            }

            // Dispatch the event to actually update the models
            this.dispatchEvent(new NetworkUpdateEvent(this.bufferedUpdates, disconnect));
            this.bufferedUpdates = [];
        }, batchTimeout);
    }
}

async function* readLinesStreamings(reader: ReadableStreamDefaultReader<Uint8Array>) {
    let decoder = new TextDecoder();
    let buffer = new Uint8Array();
    while (true) {
        let {value, done} = await reader.read();
        if (done || !value) break;
        buffer = new Uint8Array([...buffer, ...value]);
        let text = decoder.decode(buffer);
        let lines = text.split("\n");
        for (let i = 0; i < lines.length - 1; i++) {
            yield lines[i];
        }
        buffer = new Uint8Array([...buffer.slice(-1)]);
    }
}