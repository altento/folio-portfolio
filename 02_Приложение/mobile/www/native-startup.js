import { registerPlugin } from '@capacitor/core';

const FolioStartup = registerPlugin('FolioStartup');

export async function releaseStartupSplash() {
  return FolioStartup.ready();
}
