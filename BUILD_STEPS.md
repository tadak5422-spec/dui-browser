# Dui Browser — build guide

Full Chromium (Kiwi classic) based browser. Build phone par nahi hota — poora build GitHub Actions par chalta hai. Is repo me sirf patch + workflow hai.

## Pehla build

1. GitHub repo: `tadak5422-spec/dui-browser` (public).
2. Repo → **Actions** → **Build Dui Browser (arm64)** → **Run workflow**.
3. Inputs (default bhi theek hain):

   | Input | Default |
   |---|---|
   | `app_name` | `Dui Browser` |
   | `package_name` | `com.dui.browser` |
   | `source_repo` | `https://github.com/kiwibrowser/src.git` |
   | `source_ref` | `master` |
   | `make_release` | `no` |

4. Pehla run ~2–3 ghante. Baad wale runs ccache se ~10–30 min.
5. Artifact: `dui-browser-arm64` → `dui-browser-arm64.apk`. Download karke phone me install karein.

> Purana Kiwi/Dui Browser uninstall kar dena, warna signature mismatch milega. Signing key Actions me har baar naya banti hai — isliye update install nahi hoga, fresh install karna padega. Baad me fixed keystore add kar sakte hain (secure way: GitHub Secrets).

## Minimal v1 me kya hai

- Chromium omnibox: URL type karna + search (default search engine)
- Back / Forward / Reload
- Basic tabs
- Zehadar extras band: extensions, translate, sign-in, feed, cast, VR, print, WebAPK, PDF, Widevine

## Bad me add karne ke liye

- `clean/args.gn` me `enable_extensions = true` karke extensions wapas
- `clean/apply_clean.py` me `REMOVE_IDS` se jo menu item hataya hai, uski line hata kar wapas
- Naye disable/enable flags ke liye `disable_features` string edit karein
- Details: [ROADMAP.md](ROADMAP.md)

## Package ID

`chrome/android/BUILD.gn` me `manifest_package` line ko `apply_clean.py` patch karta hai. Naam badalna ho to workflow input `package_name` badlein; source me aur kuch edit karne ki zarurat nahi.
