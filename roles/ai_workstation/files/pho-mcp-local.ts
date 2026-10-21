/**
 * Local entry (Ansible ai_workstation): like main.ts, but bound to the loopback interface only.
 * PHO_BIND_ADDRESS, not HOST: zsh exports HOST as the machine name.
 */

import { serve } from '@hono/node-server';
import { getConnInfo } from '@hono/node-server/conninfo';
import { createApp } from './app';
import { loadConfig } from './config';

const config = loadConfig();
const app = createApp({ config, socketIp: (c) => getConnInfo(c).remote.address });
const hostname = process.env.PHO_BIND_ADDRESS ?? '127.0.0.1';

serve({ fetch: app.fetch, port: config.port, hostname }, (info) => {
  console.log(`[mcp] Phở Research Tools listening on http://${hostname}:${info.port}/mcp`);
});
