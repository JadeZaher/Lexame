import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { AppService } from './app.service.js';

@Controller('ipfs-api')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getHeliaVersion(): Promise<string> {
    const helia = await this.appService.getHelia();
    return 'Helia is running, PeerId ' + helia.libp2p.peerId.toString();
  }

  @Post('add')
  async addFile(@Body() file: any): Promise<string> {
    return await this.appService.addFile(file);
  }

  @Get('cat/:hash')
  async getFile(@Param('hash') hash: string): Promise<string> {
    return await this.appService.getFile(hash);
  }

  @Post('ls')
  async listFiles(@Body() options: any): Promise<string> {
    return await this.appService.listFiles(options);
  }

  async onApplicationShutdown(): Promise<void> {
    await this.appService.onApplicationShutdown();
  }
}
