import { registerPlugin } from '@capacitor/core';
import { App } from '@capacitor/app';

const FolioStartup = registerPlugin('FolioStartup');

export function addNativeBackButtonListener(listener) {
  return App.addListener('backButton', listener);
}

export function exitNativeApp() {
  return App.exitApp();
}

export async function releaseStartupSplash() {
  return FolioStartup.ready();
}
