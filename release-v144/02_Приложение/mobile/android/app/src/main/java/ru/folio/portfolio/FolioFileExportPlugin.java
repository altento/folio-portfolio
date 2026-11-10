package ru.folio.portfolio;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "FolioFileExport")
public class FolioFileExportPlugin extends Plugin {
    private static final String EXPORT_DIR = "folio-exports";

    @PluginMethod
    public void prepareExport(PluginCall call) {
        String name = call.getString("name");
        String content = call.getString("content");
        if (name == null || name.isBlank() || content == null) {
            call.reject("Не удалось подготовить содержимое файла.");
            return;
        }
        File directory = new File(getContext().getCacheDir(), EXPORT_DIR);
        if (!directory.isDirectory() && !directory.mkdirs()) {
            call.reject("Не удалось подготовить временное хранилище файла.");
            return;
        }
        removeExpiredExports(directory);
        String fileId = "folio-" + UUID.randomUUID() + ".tmp";
        File file = new File(directory, fileId);
        try (FileOutputStream stream = new FileOutputStream(file)) {
            stream.write(content.getBytes(StandardCharsets.UTF_8));
            stream.flush();
            JSObject result = new JSObject();
            result.put("fileId", fileId);
            call.resolve(result);
        } catch (Exception error) {
            file.delete();
            call.reject("Не удалось подготовить файл: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void save(PluginCall call) {
        String name = call.getString("name");
        String fileId = call.getString("fileId");
        String mimeType = call.getString("mimeType", "application/octet-stream");
        if (name == null || name.isBlank() || !isSafeFileId(fileId)) {
            call.reject("Не удалось найти подготовленный файл.");
            return;
        }
        String safeName = name.replaceAll("[\\\\/:*?\"<>|]", "_");
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType(mimeType);
        intent.putExtra(Intent.EXTRA_TITLE, safeName);
        startActivityForResult(call, intent, "saveDocumentResult");
    }

    @ActivityCallback
    private void saveDocumentResult(PluginCall call, ActivityResult result) {
        if (call == null) return;
        File source = preparedFile(call.getString("fileId"));
        try {
            if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null) {
                call.reject("Сохранение отменено.");
                return;
            }
            Uri uri = result.getData().getData();
            if (uri == null) throw new IllegalStateException("Не удалось получить путь сохранения.");
            if (source == null || !source.isFile()) {
                throw new IllegalStateException("Временная копия файла уже недоступна.");
            }
            try (FileInputStream input = new FileInputStream(source);
                 OutputStream output = getContext().getContentResolver().openOutputStream(uri, "w")) {
                if (output == null) throw new IllegalStateException("Провайдер файлов не открыл поток записи.");
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                output.flush();
            }
            JSObject resultData = new JSObject();
            resultData.put("name", uri.getLastPathSegment());
            call.resolve(resultData);
        } catch (Exception error) {
            call.reject("Не удалось сохранить файл: " + error.getMessage(), error);
        } finally {
            if (source != null) source.delete();
        }
    }

    @Override
    protected Bundle saveInstanceState() {
        return new Bundle();
    }

    private boolean isSafeFileId(String value) {
        return value != null && value.matches("folio-[0-9a-fA-F-]{36}\\.tmp");
    }

    private File preparedFile(String fileId) {
        if (!isSafeFileId(fileId)) return null;
        File directory = new File(getContext().getCacheDir(), EXPORT_DIR);
        try {
            File file = new File(directory, fileId);
            if (!file.getCanonicalPath().startsWith(directory.getCanonicalPath() + File.separator)) return null;
            return file;
        } catch (Exception error) {
            return null;
        }
    }

    private void removeExpiredExports(File directory) {
        File[] files = directory.listFiles();
        if (files == null) return;
        long cutoff = System.currentTimeMillis() - 24L * 60L * 60L * 1000L;
        for (File file : files) {
            if (file.getName().startsWith("folio-") && file.lastModified() < cutoff) file.delete();
        }
    }
}


