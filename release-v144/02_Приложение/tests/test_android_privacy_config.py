import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "mobile" / "android" / "app" / "src" / "main"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
BACKUP_DOMAINS = {
    "root",
    "file",
    "database",
    "sharedpref",
    "external",
    "device_root",
    "device_file",
    "device_database",
    "device_sharedpref",
}


class AndroidPrivacyConfigTests(unittest.TestCase):
    def test_android_disables_auto_backup_and_declares_rules(self):
        manifest = ET.parse(ANDROID / "AndroidManifest.xml").getroot()
        app = manifest.find("application")
        self.assertIsNotNone(app)
        self.assertEqual(app.get(f"{ANDROID_NS}allowBackup"), "false")
        self.assertEqual(app.get(f"{ANDROID_NS}fullBackupContent"), "@xml/backup_rules")
        self.assertEqual(app.get(f"{ANDROID_NS}dataExtractionRules"), "@xml/data_extraction_rules")

    def test_android_backup_rules_exclude_all_user_data_domains(self):
        legacy = ET.parse(ANDROID / "res" / "xml" / "backup_rules.xml").getroot()
        legacy_exclusions = {
            node.get("domain")
            for node in legacy.findall("exclude")
            if node.get("path") == "."
        }
        self.assertTrue(BACKUP_DOMAINS <= legacy_exclusions)

        modern = ET.parse(ANDROID / "res" / "xml" / "data_extraction_rules.xml").getroot()
        for transfer in ("cloud-backup", "device-transfer"):
            section = modern.find(transfer)
            self.assertIsNotNone(section)
            exclusions = {
                node.get("domain")
                for node in section.findall("exclude")
                if node.get("path") == "."
            }
            self.assertTrue(BACKUP_DOMAINS <= exclusions, transfer)


if __name__ == "__main__":
    unittest.main()
