# AUDIT - hand-rolled pieces vs established tools (2026-10-05, Cody: "replace everything with established and
# reliable tools where you can; invent only as the absolute last resort")

Rule from here: before any change, read the tool's documentation, build on its documented method, cite it in the
commit. A hand-rolled piece stays only where no established tool does the job - and that is said in the code.

| piece | was (hand-rolled) | now (established) | source | commit |
|---|---|---|---|---|
| placing photo strips on the label | guessed half-turn roll + guessed height ("most unlike strip goes on the back") | SIFT features, Lowe ratio 0.7, >=10 matches, RANSAC, estimateAffinePartial2D; chained like a panorama; no match = left out | docs.opencv.org/5.0 py_feature_homography; group__calib3d | 9ff069b |
| the label texture | AI redraw as vector art from a word list, judged in rounds | the photo IS the texture (stitched real pixels, de-glared, Real-ESRGAN) - what every photo-scanning tool does | Blender texture paint (project/image from view), Meshroom Texturing, Polycam, RealityCapture | 6cd2197 |
| the side no photo shows | color bands continued (no text) | Hunyuan3D-Paint 2.1 paints the exact label shell all the way around in ITS OWN UV layout from the cleanest photo; real pixels laid over it where seen | github.com/Tencent-Hunyuan/Hunyuan3D-2.1 (installed, proven on this Mac 10-01) | f7ba614 |
| mesh health | own hole count on bmesh (gave 3268 false holes) | trimesh is_watertight / volume / euler_number / winding; defects it found fixed in the builders (dissolve_degenerate at the lathe and at the contract gate) | trimesh.org | 02a2722 |
| reading the label's words | two brain reads must agree + own merging rules | Apple Vision text reader with its own confidence (>= 0.5) | developer.apple.com/documentation/vision/vnrecognizedtext/confidence | f24915b |
| which words are one printed line | own rules (one_per_print A/B/C/D) | KEPT, on top of Vision's lines: the same line read off several pictures must still be one line; no tool merges across pictures. Smallest it can be; 32 tests | - | ccdb863, b4b7bc7 |
| material numbers | hand-typed table | physicallybased.info v2 (CC0) snapshot: base color (linear), metalness, density for 16 kinds; roughness per kind (finish-dependent, the database lists polished) | api.physicallybased.info/v2, github.com/AntonPalmqvist/physically-based-api | 1cca484 |
| inputs to the machine | Telegram bot (Hart) + a human photo pick | the page: Cloudflare Pages Function + one KV box, polled by the Mac; Keep/Redo/Retry/Note/Add/Restart/jobs/pick/size on the page; auto-pick stays the rule | developers.cloudflare.com/pages/functions | 2f62437 |
| finding photos | own browser scraper against Google Images with "manners" | STILL HAND-ROLLED. Google's Custom Search JSON API is "closed to new customers" (developers.google.com/custom-search/v1/overview). Official alternatives need a key Cody signs up for (Brave Search API image endpoint, free tier). His call - asked. | - | - |
| cylinder unroll (photo -> flat strip) | own math (unwrap.py / mosaic.placed) | KEPT: the cylindrical projection every panorama tool uses; a Blender camera projection would need the same camera fit from the silhouette. Verified by the stitcher's registration (strips land to the pixel) | - | - |
| the judge (model vs photo, side by side) | brain asked to compare pictures | KEPT: standard "model as judge"; it compares, it never draws | - | - |
| the exact checks (size, sides, text, materials) | own measurements | KEPT where no tool exists (size vs catalog, text_found vs must_show); text read by Vision; mesh by trimesh; materials vs the database ranges | - | - |
| orchestration (queue, watchdog, self-restart, kept-work cache) | own | KEPT: small, tested (eng/test_queue 41, test_watchdog 8, test_selfrestart 10); a task queue library would not remove the Mac-specific parts | - | - |

## Still to do (in order)
1. Blender camera projection for NON-round items (boxes, cards): today panels are rectified by homography (an
   established method) - fine; projection only matters for odd shapes, which Hunyuan3D makes and paints whole.
2. Photo search through an official API once Cody picks one (Brave) - or stays on the browser path.
3. The watch: a camera in Blender ("watch it build") - after the first kept item; the page's live steps show each
   step's pictures already.
