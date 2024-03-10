import {settings} from "./settings";

const batchTimeout = 250; // ms

class NetworkUpdateEventModel {
    name: string;
    url: string;
    // TODO: Detect and manage instances of the same object (same hash, different name)
    hash: string | null;
    isRemove: boolean;

    constructor(name: string, url: string, hash: string | null, isDelete: boolean) {
        this.name = name;
        this.url = url;
        this.hash = hash;
        this.isRemove = isDelete;
    }
}

export class NetworkUpdateEvent extends Event {
    models: NetworkUpdateEventModel[];

    constructor(models: NetworkUpdateEventModel[]) {
        super("update");
        this.models = models;
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
    async load(url: string) {
        if (url.startsWith("dev+")) {
            let baseUrl = new URL(url.slice(4));
            baseUrl.searchParams.set("api_updates", "true");
            await this.monitorDevServer(baseUrl);
        } else {
            // Get the last part of the URL as the "name" of the model
            let name = url.split("/").pop();
            name = name?.split(".")[0] || `unknown-${Math.random()}`;
            // Use a head request to get the hash of the file
            let response = await fetch(url, {method: "HEAD"});
            let hash = response.headers.get("etag");
            // Only trigger an update if the hash has changed
            this.foundModel(name, hash, url, false);
        }
    }

    private async monitorDevServer(url: URL) {
        try {
            // WARNING: This will spam the console logs with failed requests when the server is down
            let response = await fetch(url.toString());
            // console.log("Monitoring", url.toString(), response);
            if (response.status === 200) {
                let lines = readLinesStreamings(response.body!.getReader());
                for await (let line of lines) {
                    if (!line || !line.startsWith("data:")) continue;
                    let data = JSON.parse(line.slice(5));
                    // console.debug("WebSocket message", data);
                    let urlObj = new URL(url);
                    urlObj.searchParams.delete("api_updates");
                    urlObj.searchParams.set("api_object", data.name);
                    this.foundModel(data.name, data.hash, urlObj.toString(), data.is_remove);
                }
            }
        } catch (e) { // Ignore errors (retry very soon)
        }
        setTimeout(() => this.monitorDevServer(url), settings.monitorEveryMs);
        return;
    }

    private foundModel(name: string, hash: string | null, url: string, isRemove: boolean) {
        let prevHash = this.knownObjectHashes[name];
        let hashToCheck = hash + (isRemove ? "-remove" : "");
        // console.debug("Found model", name, "with hash", hash, "and previous hash", prevHash);
        if (!hash || hashToCheck !== prevHash) {
            this.knownObjectHashes[name] = hash;
            let newModel = new NetworkUpdateEventModel(name, url, hash, isRemove);
            this.bufferedUpdates.push(newModel);

            // Optimization: try to batch updates automatically for faster rendering
            if (this.batchTimeout !== null) clearTimeout(this.batchTimeout);
            this.batchTimeout = setTimeout(() => {
                this.dispatchEvent(new NetworkUpdateEvent(this.bufferedUpdates));
                this.bufferedUpdates = [];
            }, batchTimeout);
        }
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