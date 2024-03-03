import {settings} from "./settings";

export class NetworkUpdateEvent extends Event {
    name: string;
    url: string;

    constructor(name: string, url: string) {
        super("update");
        this.name = name;
        this.url = url;
    }
}

/** Listens for updates and emits events when a model changes */
export class NetworkManager extends EventTarget {
    private knownObjectHashes: { [name: string]: string } = {};

    /**
     * Tries to load a new model (.glb) from the given URL.
     *
     * If the URL uses the websocket protocol (ws:// or wss://), the server will be continuously monitored for changes.
     * In this case, it will only trigger updates if the name or hash of any model changes.
     *
     * Updates will be emitted as "update" events, including the download URL and the model name.
     */
    async load(url: string) {
        if (url.startsWith("ws://") || url.startsWith("wss://")) {
            this.monitorWebSocket(url);
        } else {
            // Get the last part of the URL as the "name" of the model
            let name = url.split("/").pop();
            name = name?.split(".")[0] || `unknown-${Math.random()}`;
            // Use a head request to get the hash of the file
            let response = await fetch(url, {method: "HEAD"});
            let hash = response.headers.get("etag");
            // Only trigger an update if the hash has changed
            this.foundModel(name, hash, url);
        }
    }

    private monitorWebSocket(url: string) {
        // WARNING: This will spam the console logs with failed requests when the server is down
        let ws = new WebSocket(url);
        ws.onmessage = (event) => {
            let data = JSON.parse(event.data);
            console.debug("WebSocket message", data);
            let urlObj = new URL(url);
            urlObj.protocol = urlObj.protocol === "ws:" ? "http:" : "https:";
            urlObj.searchParams.set("api_object", data.name);
            this.foundModel(data.name, data.hash, urlObj.toString());
        };
        ws.onerror = () => ws.close();
        ws.onclose = () => setTimeout(() => this.monitorWebSocket(url), settings.monitorEveryMs);
        let timeoutFaster = setTimeout(() => ws.close(), settings.monitorOpenTimeoutMs);
        ws.onopen = () => clearTimeout(timeoutFaster);
    }

    private foundModel(name: string, hash: string, url: string) {
        let prevHash = this.knownObjectHashes[name];
        if (!hash || hash !== prevHash) {
            this.knownObjectHashes[name] = hash;
            this.dispatchEvent(new NetworkUpdateEvent(name, url));
        }
    }
}