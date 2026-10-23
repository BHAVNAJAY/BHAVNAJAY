# Hero 3D model renderer

Renders `assets/hero/womanfinal.glb` to a sway turntable (PNG frames, transparent background) that
`scripts/build_hero.py` composites into the banner. Needs Node and Google Chrome.

```bash
cd scripts/model
npm install
node run.mjs ../../assets/hero/womanfinal.glb ../../assets/source/model-frames 300 430 48 14
cd ../..
python3 scripts/build_hero.py
```

Arguments: glb path, output folder, width, height, frame count, sway amplitude in degrees.
Edit the Chrome path at the top of `run.mjs` if Chrome is installed elsewhere.
