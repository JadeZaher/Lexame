import { Injectable } from '@nestjs/common';
import type { HeliaLibp2p } from 'helia';
import { unixfs } from '@helia/unixfs';
import { CID } from 'multiformats/cid';
import { toString as uint8ArrayToString } from 'uint8arrays/to-string';
import { fromString as uint8ArrayFromString } from 'uint8arrays/from-string';

@Injectable()
export class AppService {
  private helia?: HeliaLibp2p;
  private fs: any;

  async getHelia(): Promise<HeliaLibp2p> {
    if (this.helia == null) {
      const { createHelia } = await import('helia');
      this.helia = await createHelia();
      this.fs = unixfs(this.helia);
    }

    return this.helia;
  }

  async addFile(file: any): Promise<string> {
    await this.getHelia();
    
    try {
      // Convert file content to Uint8Array if it's a string
      let content: Uint8Array;
      if (typeof file.content === 'string') {
        content = uint8ArrayFromString(file.content);
      } else if (Buffer.isBuffer(file.content)) {
        content = new Uint8Array(file.content);
      } else if (file.content instanceof Uint8Array) {
        content = file.content;
      } else {
        // If it's an object, stringify it
        content = uint8ArrayFromString(JSON.stringify(file.content));
      }

      // Add the file to IPFS
      const cid = await this.fs.addBytes(content);
      
      // Return the CID as a string
      return cid.toString();
    } catch (error) {
      console.error('Error adding file to IPFS:', error);
      throw new Error(`Failed to add file to IPFS: ${error.message}`);
    }
  }

  async getFile(hash: string): Promise<string> {
    await this.getHelia();
    
    try {
      // Parse the CID from the hash string
      const cid = CID.parse(hash);
      
      // Get the file content as a Uint8Array
      const chunks: Uint8Array[] = [];
      for await (const chunk of this.fs.cat(cid)) {
        chunks.push(chunk);
      }
      
      // Concatenate chunks into a single Uint8Array
      const allChunks = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0));
      let offset = 0;
      for (const chunk of chunks) {
        allChunks.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Convert the Uint8Array to a string
      return uint8ArrayToString(allChunks);
    } catch (error) {
      console.error('Error getting file from IPFS:', error);
      throw new Error(`Failed to get file from IPFS: ${error.message}`);
    }
  }

  async listFiles(options: any): Promise<string> {
    await this.getHelia();
    
    try {
      const path = options.path || '/';
      const cid = CID.parse(path);
      
      let entries = [];
      for await (const entry of this.fs.ls(cid)) {
        entries.push({
          name: entry.name,
          cid: entry.cid.toString(),
          size: entry.size,
          type: entry.type
        });
      }
      
      return JSON.stringify(entries);
    } catch (error) {
      console.error('Error listing files from IPFS:', error);
      throw new Error(`Failed to list files from IPFS: ${error.message}`);
    }
  }

  async onApplicationShutdown(): Promise<void> {
    if (this.helia != null) {
      await this.helia.stop();
    }
  }
}
