# Android v148 emulator start attempt — 2026-11-06

## Environment

- Host CPU: 12th Gen Intel Core i5-12400F, x86_64.
- `Win32_Processor.VirtualizationFirmwareEnabled`: `False`.
- Installed Android Emulator: 37.2.13.0.
- Installed API 36 Google APIs images: x86_64 and arm64-v8a.
- No physical Android device was attached (`adb devices -l` returned no devices).

## Attempts

1. Started existing `FolioQA_API36` with `-accel off -gpu swiftshader_indirect -no-snapshot`. The emulator process exited with Windows status `-1073741819` (`0xC0000005`); ADB did not expose a device. The log warned that x86_64 emulation may not work without hardware acceleration.
2. Installed the official API 36 Google APIs ARM64 image and started a dedicated phone-sized AVD. Emulator exited before boot with: `Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host. System image must match the host architecture.`

## Result and boundary

No Android v148 APK was installed or launched; no offline app runtime result or emulator screenshot is claimed. No Folio user profile/database was read or modified. A physical Android phone or enabling virtualization in firmware is needed for a meaningful Android runtime pass on this host. Previous v147 AVD evidence remains historical and is not represented as v148 verification.
