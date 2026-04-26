from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.ai_builder_service import AiBuildJob, AiBuildPlan


class IllustratorService:
    def build_ai_files(
        self,
        illustrator_path: Path,
        plan: AiBuildPlan,
    ) -> Path:
        if not illustrator_path.exists():
            raise FileNotFoundError(f"Illustrator executable does not exist: {illustrator_path}")
        if not plan.jobs:
            raise ValueError("No AI build jobs were created.")

        runnable_jobs = [job for job in plan.jobs if job.template_path.exists()]
        if not runnable_jobs:
            raise FileNotFoundError("No build jobs have existing template files.")

        plan.generated_set_dir.mkdir(parents=True, exist_ok=True)
        script_path = plan.generated_set_dir / "_build_ai_files.jsx"
        log_path = plan.generated_set_dir / "_build_ai_files.log"
        script_path.write_text(self._build_jsx(runnable_jobs, log_path), encoding="utf-8")

        subprocess.Popen([str(illustrator_path), str(script_path)])
        return script_path

    def open_ai_files(
        self,
        illustrator_path: Path,
        generated_set_dir: Path,
    ) -> list[Path]:
        if not illustrator_path.exists():
            raise FileNotFoundError(f"Illustrator executable does not exist: {illustrator_path}")

        ai_files = sorted(
            path
            for path in generated_set_dir.glob("*.ai")
            if path.is_file()
        )
        if not ai_files:
            raise FileNotFoundError(f"No generated AI files found in: {generated_set_dir}")

        subprocess.Popen([str(illustrator_path), *[str(path) for path in ai_files]])
        return ai_files

    def _build_jsx(self, jobs: list[AiBuildJob], log_path: Path) -> str:
        payload = {
            "logPath": str(log_path),
            "jobs": [
                {
                    "slot": job.slot_name,
                    "template": str(job.template_path),
                    "output": str(job.output_path),
                    "layers": [
                        {"name": layer, "svg": str(svg_path)}
                        for layer, svg_path in job.layer_svgs.items()
                    ],
                }
                for job in jobs
            ],
        }
        payload_json = json.dumps(payload)
        return f"""#target illustrator
(function () {{
    var payload = {payload_json};
    var previousInteractionLevel = app.userInteractionLevel;
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

    function writeLog(message) {{
        var file = new File(payload.logPath);
        file.open("a");
        file.writeln(message);
        file.close();
    }}

    function findLayer(container, name) {{
        for (var i = 0; i < container.layers.length; i++) {{
            var layer = container.layers[i];
            if (layer.name === name) {{
                return layer;
            }}
        }}
        return null;
    }}

    function importSvgIntoLayer(doc, layerName, svgPath) {{
        var targetLayer = findLayer(doc, layerName);
        if (!targetLayer) {{
            writeLog("Missing Illustrator layer '" + layerName + "' in " + doc.name);
            return;
        }}

        var svgFile = new File(svgPath);
        if (!svgFile.exists) {{
            writeLog("Missing SVG file for layer '" + layerName + "': " + svgPath);
            return;
        }}

        var wasLocked = targetLayer.locked;
        var wasVisible = targetLayer.visible;
        targetLayer.locked = false;
        targetLayer.visible = true;

        var sourceDoc = app.open(svgFile);
        var importedCount = 0;
        for (var i = sourceDoc.pageItems.length - 1; i >= 0; i--) {{
            sourceDoc.pageItems[i].duplicate(targetLayer, ElementPlacement.PLACEATBEGINNING);
            importedCount++;
        }}
        sourceDoc.close(SaveOptions.DONOTSAVECHANGES);

        doc.activate();
        targetLayer.locked = wasLocked;
        targetLayer.visible = wasVisible;
        writeLog("Imported " + importedCount + " item(s) into layer '" + layerName + "'");
    }}

    try {{
        for (var j = 0; j < payload.jobs.length; j++) {{
            var job = payload.jobs[j];
            var doc = null;
            try {{
                writeLog("Building " + job.slot);
                doc = app.open(new File(job.template));
                for (var i = 0; i < job.layers.length; i++) {{
                    importSvgIntoLayer(doc, job.layers[i].name, job.layers[i].svg);
                }}
                doc.saveAs(new File(job.output));
                doc.close(SaveOptions.DONOTSAVECHANGES);
                doc = null;
                writeLog("Saved " + job.output);
            }} catch (error) {{
                writeLog("ERROR " + job.slot + ": " + error);
                if (doc) {{
                    try {{
                        doc.close(SaveOptions.DONOTSAVECHANGES);
                    }} catch (closeError) {{
                        writeLog("ERROR closing " + job.slot + ": " + closeError);
                    }}
                }}
            }}
        }}
    }} finally {{
        app.userInteractionLevel = previousInteractionLevel;
    }}
}}());
"""
