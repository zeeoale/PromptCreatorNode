import { app } from "/scripts/app.js";

const EXT_NAME = "PromptCreatorNode.PromptBuilderDynamicWorld";
const DATA_URL = "/extensions/PromptCreatorNode/world_options.json";

let WORLD_CACHE = null;

async function loadWorldData() {
  if (WORLD_CACHE) return WORLD_CACHE;
  const res = await fetch(DATA_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${DATA_URL} (${res.status})`);
  WORLD_CACHE = await res.json();
  return WORLD_CACHE;
}

function setComboValues(widget, values) {
  if (!widget || !widget.options) return;
  widget.options.values = values;

  // se il valore corrente non esiste più, fallback al primo
  if (!values.includes(widget.value)) {
    widget.value = values[0];
  }
}

function getWidget(node, name) {
  return node.widgets?.find(w => w.name === name);
}

function uniqueSorted(arr) {
  return Array.from(new Set(arr)).filter(Boolean).sort();
}

function buildPickValues(basePrefix, items) {
  // basePrefix = ["none","random"] ...
  return basePrefix.concat(items || []);
}

function updateBuilderWidgets(node) {
  const jsonWidget = getWidget(node, "json_name");
  if (!jsonWidget) return;

  const worldName = jsonWidget.value;
  if (!worldName) return;

  loadWorldData().then(db => {
    const w = db[worldName];
    if (!w) return;

    // COLOR_REALM: ["none","auto","random"] + realms
    const crWidget = getWidget(node, "color_realm");
    if (crWidget) {
      const realms = w["COLOR_REALM"] || [];
      setComboValues(crWidget, ["none", "auto", "random", ...realms]);
    }

    // Single categories
    const map = [
      ["epochs_pick", "EPOCHS"],
      ["outfits_pick", "OUTFITS"],
      ["lighting_pick", "LIGHTING"],
      ["backgrounds_pick", "BACKGROUNDS"],
      ["poses_pick", "POSES"],
      ["expressions_pick", "EXPRESSIONS"],
      ["camera_angles_pick", "CAMERA_ANGLES"],
      ["atmospheres_pick", "ATMOSPHERES"]
    ];

    for (const [widgetName, key] of map) {
      const ww = getWidget(node, widgetName);
      if (!ww) continue;
      const vals = w[key]?.["__all__"] || [];
      setComboValues(ww, ["none", "random", ...vals]);
    }

    // Multi pick lists: union of OBJECTS + ACCESSORIES from THIS world
    const objAll = w["OBJECTS"]?.["__all__"] || [];
    const accAll = w["ACCESSORIES"]?.["__all__"] || [];
    const multiUnion = uniqueSorted([...objAll, ...accAll]);

    const objPick = getWidget(node, "objects_pick");
    if (objPick) setComboValues(objPick, ["none", ...multiUnion]);

    const accPick = getWidget(node, "accessories_pick");
    if (accPick) setComboValues(accPick, ["none", ...multiUnion]);

    node.setDirtyCanvas(true, true);
  }).catch(err => {
    console.warn("[PromptBuilderDynamicWorld] update failed:", err);
  });
}

app.registerExtension({
  name: EXT_NAME,

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "PromptBuilderNode") return;

    const origCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      origCreated?.apply(this, arguments);

      // Aggiorna subito al primo render
      updateBuilderWidgets(this);

      // Aggiorna quando cambia json_name
      const jsonWidget = getWidget(this, "json_name");
      if (jsonWidget) {
        const origCb = jsonWidget.callback;
        jsonWidget.callback = (v) => {
          origCb?.(v);
          updateBuilderWidgets(this);
        };
      }
    };
  }
});
