package ru.folio.portfolio;

import android.os.Handler;
import android.os.Looper;
import android.os.Bundle;
import androidx.core.splashscreen.SplashScreen;
import java.util.concurrent.atomic.AtomicBoolean;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private static final AtomicBoolean webReady = new AtomicBoolean(false);

    @Override
    public void onCreate(Bundle savedInstanceState) {
        SplashScreen splashScreen = SplashScreen.installSplashScreen(this);
        webReady.set(false);
        splashScreen.setKeepOnScreenCondition(() -> !webReady.get());
        registerPlugin(FolioFileExportPlugin.class);
        registerPlugin(FolioStartupPlugin.class);
        super.onCreate(savedInstanceState);
        new Handler(Looper.getMainLooper()).postDelayed(() -> webReady.set(true), 15_000);
    }

    static void markWebReady() {
        webReady.set(true);
    }
}
