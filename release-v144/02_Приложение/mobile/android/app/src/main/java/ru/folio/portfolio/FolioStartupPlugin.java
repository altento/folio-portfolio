package ru.folio.portfolio;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "FolioStartup")
public class FolioStartupPlugin extends Plugin {
    @PluginMethod
    public void ready(PluginCall call) {
        MainActivity.markWebReady();
        call.resolve();
    }
}
