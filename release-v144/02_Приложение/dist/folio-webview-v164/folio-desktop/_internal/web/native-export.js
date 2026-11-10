import { registerPlugin } from '@capacitor/core';

const FolioFileExport = registerPlugin('FolioFileExport');

export async function saveNativeFile(name, content, type) {
  const mimeType = String(type || 'application/octet-stream').split(';', 1)[0];
  const { fileId } = await FolioFileExport.prepareExport({
    name,
    content: String(content)
  });
  return FolioFileExport.save({ name, fileId, mimeType });
}
