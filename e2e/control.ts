import * as net from "net";
import * as fs from "fs";

let _controlPort: number | null = null;

function getControlPort(): number {
  if (_controlPort !== null) return _controlPort;
  try {
    const content = fs.readFileSync(".e2e_control_port", "utf-8").trim();
    _controlPort = parseInt(content, 10);
  } catch {
    _controlPort = 32324; // fallback default
  }
  return _controlPort;
}

/**
 * Client for the yacv-server control endpoint.
 * Sends JSON commands to the server's control port.
 */
export class ServerControl {
  /** Send a JSON command to the control endpoint and wait for response. */
  private async sendCommand(cmd: object): Promise<any> {
    return new Promise((resolve, reject) => {
      const client = new net.Socket();
      const timeout = setTimeout(() => {
        client.destroy();
        reject(new Error("Control endpoint timeout"));
      }, 5000);

      const port = getControlPort();
      client.connect(port, "localhost", () => {
        client.write(JSON.stringify(cmd) + "\n");
      });

      let data = "";
      client.on("data", (chunk) => {
        data += chunk.toString();
        clearTimeout(timeout);
        client.destroy();
      });

      client.on("close", () => {
        clearTimeout(timeout);
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve({ error: `Failed to parse response: ${data}` });
        }
      });

      client.on("error", (err) => {
        clearTimeout(timeout);
        reject(err);
      });
    });
  }

  /** Show a primitive model in the viewer. */
  async showModel(type: "box" | "sphere" | "cylinder", name: string, params: Record<string, number> = {}, autoClear: boolean = false): Promise<any> {
    return this.sendCommand({
      action: "show",
      type,
      name,
      auto_clear: autoClear,
      ...params,
    });
  }

  /** Remove a model by name. */
  async removeModel(name: string): Promise<any> {
    return this.sendCommand({ action: "remove", name });
  }

  /** Clear all models. */
  async clearModels(): Promise<any> {
    return this.sendCommand({ action: "clear" });
  }

  /** Ping the control endpoint to check if it's alive. */
  async ping(): Promise<any> {
    return this.sendCommand({ action: "ping" });
  }
}
