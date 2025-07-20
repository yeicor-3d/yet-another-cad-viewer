// B66 encoding and decoding functions for compact url query parameter values. https://gist.github.com/danneu/6755394
const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-_~";

export function b66Encode(data: Uint8Array): string {
    let result = "";
    let bits = 0;
    let value = 0;

    for (let byte of data) {
        value = (value << 8) | byte;
        bits += 8;

        while (bits >= 6) {
            bits -= 6;
            result += alphabet[(value >> bits) & 0x3F];
        }
    }

    if (bits > 0) {
        result += alphabet[(value << (6 - bits)) & 0x3F];
    }

    return result;
}

export function b66Decode(encoded: string): Uint8Array {
    let result = [];
    let bits = 0;
    let value = 0;

    for (let char of encoded) {
        const index = alphabet.indexOf(char);
        if (index === -1) {
            throw new Error(`Invalid character '${char}' in B66 encoded string.`);
        }

        value = (value << 6) | index;
        bits += 6;

        while (bits >= 8) {
            bits -= 8;
            result.push((value >> bits) & 0xFF);
        }
    }

    if (bits > 0) {
        // If there are leftover bits, they should not be present in a valid B66 encoding.
        if (value << (8 - bits)) {
            throw new Error("Invalid B66 encoding: leftover bits.");
        }
    }

    return new Uint8Array(result);
}