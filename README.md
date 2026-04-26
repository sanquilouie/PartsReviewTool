# Ninja Shibui Parts Review MVP

Strict MVP desktop tool for reviewing raw SVG parts extracted from SWF files, manually renaming them, and organizing them into XML-derived folders.

## Scope

This app does:

- choose a SWF file
- run JPEXS extraction into a per-SWF `raw_svg` folder
- automatically load or generate the matching JPEXS XML
- organize extracted SVGs into XML-derived folders
- show organized SVGs in a thumbnail gallery
- preview the selected SVG
- manually enter a new filename
- quickly save common filenames: `skin.svg`, `layer_01.svg`, `layer_02.svg`
- choose any folder to view SVGs recursively
- save the renamed SVG into the organized folder structure
- build Illustrator working files from organized slot folders
- open generated AI files in Illustrator

This app does not do PNG export, Unity import, semantic filename guessing, or automatic classification.

## Setup

Use Python 3.8+ on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## JPEXS Configuration

The output root, JPEXS executable, Illustrator executable, template folder, and generated AI root are configured from `Settings`. These are saved to:

```text
config/jpexs_config.json
```

The default command template is isolated there:

```json
{
  "jpexs_path": "",
  "illustrator_path": "",
  "templates_folder": "",
  "generated_ai_root": "",
  "scale_percent": 400,
  "args_template": [
    "{jpexs_path}",
    "-format",
    "shape:svg",
    "-zoom",
    "{scale_factor}",
    "-export",
    "shape",
    "{output_dir}",
    "{swf_path}"
  ]
}
```

JPEXS CLI options can differ by version. If your installed JPEXS needs explicit SVG or scale arguments, adjust only `args_template`. Available placeholders are:

- `{jpexs_path}`
- `{swf_path}`
- `{output_dir}`
- `{scale_percent}`
- `{scale_factor}`

## Expected Folder Structure

The app uses the existing repo folders:

```text
workspace/
  raw_svg/
    set_01_0/
      extracted/
        part_001.svg
        part_002.svg
  organized/
    set_01_0/
      upper_body/
        skin.svg
        layer_01.svg
  generated_ai/
    set_01_0/
      upper_body.ai

```

When you click `Save / Move`, raw extracted SVGs are copied into the organized folder. Files already in the organized folder are renamed or moved in place.

## XML Folder Grouping

If an XML version of the SWF sits beside the SWF with the same filename stem, the app detects it automatically after you choose or extract the SWF.

Example:

```text
set_01_1.swf
set_01_1.xml
```

After a successful `Extract SVGs`, the app automatically applies XML folder grouping. It handles XML like this:

- if `set_01_1.xml` already exists beside `set_01_1.swf`, it loads that file
- otherwise it runs JPEXS `-swf2xml`
- generated XML is saved under `workspace/raw_svg/<session>/<session>.xml`

The app reads:

- `SymbolClassTag` names, such as `upper_body`, `lower_body`, `left_hand`
- `DefineSpriteTag` / `PlaceObject*Tag` parent-child relationships
- `DefineShape*Tag shapeId`, which matches exported files like `13.svg`

Each raw SVG is copied into:

```text
workspace/organized/<session>/<symbol_name>/<shape_id>.svg
```

This is structural grouping from the XML, not filename guessing. The app preserves the original SVG filename so you can still manually rename parts during review.

After `Extract SVGs`, the app extracts raw SVGs, loads or generates the matching XML, applies XML folder grouping, and switches the gallery to the organized folder view. Use `Choose Folder to View` to review any organized folder or subfolder.

## Illustrator Build

Configure these in `Settings` before building:

- Illustrator executable path
- Templates folder
- Generated AI root

Template names and expected layers are defined in:

```text
config/slot_config.json
```

The config shape is:

```json
{
  "slots": {
    "upper_body": {
      "template": "tpl_upper_body.ai",
      "layers": ["skin", "layer_01", "layer_02"],
      "output": "upper_body.ai",
      "size": [768, 768]
    }
  }
}
```

Use the Phase 2 flow:

1. Load or generate an organized set folder.
2. Click `Build AI Files`.
3. Illustrator receives a JSX build script.
4. One AI working file is saved per recognized slot under `workspace/generated_ai/<set>/`.
5. Click `Open Generated AI Folder` to inspect the output.
6. Click `Open All AI in Illustrator` to open the generated AI files as separate Illustrator tabs.

The build uses matching filenames only: `skin.svg` goes to layer `skin`, `layer_01.svg` goes to layer `layer_01`, and `layer_02.svg` goes to layer `layer_02`. Unknown SVG files are logged and ignored. Missing templates or missing SVG layer files are logged as warnings.

## Later Illustrator Integration

Later work can improve placement and export behavior, but this phase intentionally stops at generated/opened Illustrator working files.
