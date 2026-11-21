#!/usr/bin/env python3
"""Apply the 'Dui Browser' minimal-v1 source patch.

Usage:
    python3 clean/apply_clean.py <path-to-src> "<App Name>" "<package.id>"

Idempotent: safe to re-run. Warnings are printed for things that are not found
(when upstream changes), but the build is not aborted.
"""
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
APP_NAME = sys.argv[2] if len(sys.argv) > 2 else "Dui Browser"
PACKAGE_NAME = sys.argv[3] if len(sys.argv) > 3 else "com.dui.browser"

if not (SRC / "chrome" / "android" / "java").exists():
    sys.exit(f"ERROR: {SRC} does not look like a Chromium/Kiwi src checkout")

print(f"[dui] src     = {SRC}")
print(f"[dui] app     = {APP_NAME}")
print(f"[dui] package = {PACKAGE_NAME}")


def write_if_changed(path: Path, text: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8", errors="ignore") == text:
        return
    path.write_text(text, encoding="utf-8")
    print(f"[dui] wrote {path.relative_to(SRC)}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def remove_xml_item(text: str, item_id: str):
    """Remove an <item android:id="@+id/<item_id>" ...> block, nested-safe."""
    marker = 'android:id="@+id/%s"' % item_id
    idx = text.find(marker)
    if idx == -1:
        return text, False

    start = text.rfind("<item", 0, idx)
    if start == -1:
        return text, False

    tag_end = text.find(">", idx)
    if tag_end == -1:
        return text, False

    if text[tag_end - 1] == "/":  # <item ... />
        end = tag_end + 1
    else:
        depth = 0
        pos = tag_end + 1
        end = -1
        while pos < len(text):
            nxt_open = text.find("<item", pos)
            nxt_close = text.find("</item>", pos)
            if nxt_close == -1:
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                gt = text.find(">", nxt_open)
                if gt == -1:
                    break
                # Self-closing child (<item ... />) does not open a block.
                if text[gt - 1] != "/":
                    depth += 1
                pos = gt + 1
            else:
                if depth == 0:
                    end = nxt_close + len("</item>")
                    break
                depth -= 1
                pos = nxt_close + len("</item>")
        if end == -1:
            return text, False

    line_start = text.rfind("\n", 0, start) + 1
    return text[:line_start] + text[end:], True


def remove_xml_tag(text: str, tag: str, name_fragment: str):
    """Remove a manifest <activity|service|receiver ... name='...' ...> block."""
    pattern = re.compile(
        r"\n[ \t]*<" + re.escape(tag) + r"\b[^>]*" + re.escape(name_fragment) +
        r"[^>]*(?:/>|>[\s\S]*?</" + re.escape(tag) + r">)",
        re.IGNORECASE,
    )
    new, n = pattern.subn("", text)
    return new, n > 0


# -------------------------------------------------------------
# 1. App name / widget labels
# -------------------------------------------------------------
res_chromium = SRC / "chrome" / "android" / "java" / "res_chromium"
for path in sorted(res_chromium.glob("values*/strings.xml")) + sorted(
    res_chromium.glob("values*/channel_constants.xml")
):
    text = read(path)
    new = text
    replacements = {
        "Kiwi Browser (classic)": APP_NAME,
        "Kiwi Browser Next": APP_NAME,
        "Kiwi Browser": APP_NAME,
        "Kiwi bookmarks": f"{APP_NAME} bookmarks",
        "Kiwi search": f"{APP_NAME} search",
    }
    for old, value in replacements.items():
        new = new.replace(old, value)
    if new != text:
        write_if_changed(path, new)

# -------------------------------------------------------------
# 1b. Package ID override
#     chrome/android/BUILD.gn contains:
#       manifest_package = "com.kiwibrowser.browser.classic"
#     The AndroidManifest template uses {{ manifest_package }}, so this single
#     line is enough to rebrand the package without touching generated files.
# -------------------------------------------------------------
build_gn = SRC / "chrome" / "android" / "BUILD.gn"
if build_gn.exists():
    text = read(build_gn)
    new, n = re.subn(
        r'(\bmanifest_package\s*=\s*")[^"]+(")',
        lambda m: m.group(1) + PACKAGE_NAME + m.group(2),
        text,
        count=1,
    )
    if n:
        write_if_changed(build_gn, new)
        print(f"[dui] package patched -> {PACKAGE_NAME}")
    else:
        print("[dui] WARN manifest_package line not found")
else:
    print(f"[dui] WARN BUILD.gn not found: {build_gn}")

# -------------------------------------------------------------
# 2. Menu clutter
# -------------------------------------------------------------
REMOVE_IDS = [
    "update_menu_id",                 # update check
    "move_to_other_window_menu_id",   # multi-window
    "share_row_menu_id",              # share / direct share
    "translate_menu_id",              # translate
    "help_id",                        # help & feedback
    "enter_vr_id",                    # Daydream / VR
    "open_webapk_id",                 # WebAPK
    "reader_mode_prefs_id",           # reader mode prefs
]

menu = res_chromium.parent / "res" / "menu" / "main_menu.xml"
if menu.exists():
    text = read(menu)
    removed = []
    for item_id in REMOVE_IDS:
        text, ok = remove_xml_item(text, item_id)
        if ok:
            removed.append(item_id)
    write_if_changed(menu, text)
    print(f"[dui] menu removed: {', '.join(removed) if removed else '(none / already clean)'}")
else:
    print(f"[dui] WARN menu not found: {menu}")

# -------------------------------------------------------------
# 3. Manifest: sign-in / sync / GCM / VR noise
# -------------------------------------------------------------
manifest = SRC / "chrome" / "android" / "java" / "AndroidManifest.xml"
if manifest.exists():
    text = read(manifest)
    targets = [
        ("activity", "org.chromium.chrome.browser.signin."),
        ("activity", "org.chromium.chrome.browser.sync.ui.PassphraseActivity"),
        ("receiver", "org.chromium.chrome.browser.services.AccountsChangedReceiver"),
        ("service", "org.chromium.chrome.browser.services.gcm."),
        ("service", "com.google.ipc.invalidation.ticl.android2.channel."),
        ("activity", "org.chromium.chrome.browser.vr_shell."),
        ("activity", "org.chromium.chrome.browser.vr.Vr"),
        ("activity", "org.chromium.chrome.browser.printing.PrintShareActivity"),
        ("activity", "org.chromium.chrome.browser.media.remote.ExpandedControllerActivity"),
    ]
    for tag, fragment in targets:
        text, ok = remove_xml_tag(text, tag, fragment)
        if not ok:
            print(f"[dui]   (manifest) not found: {tag} ~ {fragment}")
    write_if_changed(manifest, text)
else:
    print(f"[dui] WARN manifest not found: {manifest}")

# -------------------------------------------------------------
# 4. Java: old Chromium JDK 8 ke saath test hua tha. Runner par JDK 17
#    "-source 8" warning deta hai aur -Werror use error bana deta hai.
#    Warning ko fatal na hone dein.
# -------------------------------------------------------------
javac_py = SRC / "build" / "android" / "gyp" / "javac.py"
if javac_py.exists():
    text = read(javac_py)
    new = text.replace(
        "javac_cmd.extend(['-Xlint:unchecked', '-Werror'])",
        "javac_cmd.extend(['-Xlint:unchecked'])",
    )
    if new != text:
        write_if_changed(javac_py, new)
        print("[dui] javac -Werror removed")
    else:
        print("[dui] javac patch already applied (or pattern changed)")

    # JDK 9+ me rt.jar hota hi nahi. Purana javac.py use bootclasspath me
    # blindly add karta hai -> "No such file or directory: .../rt.jar".
    old_rt = (
        "    rt_jar = os.path.join(jdk_dir, 'jre', 'lib', 'rt.jar')\n"
        "    options.bootclasspath.append(rt_jar)\n"
    )
    new_rt = (
        "    rt_jar = os.path.join(jdk_dir, 'jre', 'lib', 'rt.jar')\n"
        "    if os.path.exists(rt_jar):\n"
        "      options.bootclasspath.append(rt_jar)\n"
    )
    current = read(javac_py)
    new = current.replace(old_rt, new_rt)
    if new != current:
        write_if_changed(javac_py, new)
        print("[dui] javac rt.jar existence check added")
    else:
        print("[dui] javac rt.jar patch already applied (or pattern changed)")
else:
    print(f"[dui] WARN javac.py not found: {javac_py}")

# -------------------------------------------------------------
# 5. Android lint: purana SDK lint JDK 8 ka JAXB (javax.xml.bind)
#    maangta hai, jo JDK 11 me nahi hota. APK banane ke liye lint
#    zaroori nahi, isliye usse no-op bana rahe hain (outputs phir bhi
#    likhta hai taake ninja khush rahe).
# -------------------------------------------------------------
lint_py = SRC / "build" / "android" / "gyp" / "lint.py"
if lint_py.exists():
    text = read(lint_py)
    marker = "Dui Browser: Android lint skipped"
    if marker in text:
        print("[dui] lint patch already applied")
    else:
        old_lint = (
            "  with build_utils.TempDir() as temp_dir:\n"
            "    _ProcessConfigFile()\n"
            "\n"
            "    cmd = [\n"
        )
        new_lint = (
            "  _ProcessConfigFile()\n"
            "  # " + marker + " (JDK 11 me JAXB nahi hai).\n"
            "  with open(result_path, 'w') as f:\n"
            "    f.write('<issues></issues>')\n"
            "  return\n"
            "\n"
            "  with build_utils.TempDir() as temp_dir:\n"
            "    _ProcessConfigFile()\n"
            "\n"
            "    cmd = [\n"
        )
        new = text.replace(old_lint, new_lint)
        if new != text:
            write_if_changed(lint_py, new)
            print("[dui] lint disabled (no-op)")
        else:
            print("[dui] WARN lint.py pattern not found; lint may still run")
else:
    print(f"[dui] WARN lint.py not found: {lint_py}")

# -------------------------------------------------------------
# 6. policy writer: PyPy2 me dict iteration order alag hoti hai.
#    Original code backslash ko apostrophe ke baad escape karta hai,
#    jisse "\\'" ban jata hai aur aapt error deta hai.
#    Escape order fix karo: backslash -> apostrophe -> quote -> XML.
# -------------------------------------------------------------
policy_writer = (
    SRC / "components" / "policy" / "tools" / "template_writers" /
    "writers" / "android_policy_writer.py"
)
if policy_writer.exists():
    text = read(policy_writer)
    marker = "Dui Browser: PyPy2 dict order"
    if marker in text:
        print("[dui] policy writer patch already applied")
    else:
        new_escape = r'''  # Dui Browser: PyPy2 dict order doubled backslashes before apostrophes.
  # Fixed order: backslash, apostrophe, quote, then XML escaping.
  resource = resource.replace('\\', '\\\\')
  resource = resource.replace("'", "\\'")
  resource = resource.replace('"', '\\"')
  return xml_escape.escape(resource)'''
        lines = text.splitlines(True)
        new_lines = []
        replaced = False
        for line in lines:
            if line.strip().startswith("return xml_escape.escape(resource,"):
                new_lines.append(new_escape + ("\n" if line.endswith("\n") else ""))
                replaced = True
            else:
                new_lines.append(line)
        if replaced:
            new = "".join(new_lines)
            write_if_changed(policy_writer, new)
            print("[dui] policy resource escaping fixed")
        else:
            print("[dui] WARN policy writer pattern not found")
else:
    print(f"[dui] WARN policy writer not found: {policy_writer}")

print("[dui] done")
