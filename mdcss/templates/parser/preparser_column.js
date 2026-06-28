const columnRegex = /(^-?\|\|\|-?:?\d*(?:%|px)?:?$)/m;
function parseCulumnSpec(spec) {
    let type = "separator";
    let width = "";
    let align = "";
    if (spec.startsWith("|||-")) {
        type = "start";
        spec = spec.slice(4);
    } else if (spec.startsWith("-|||")) {
        if (spec.length != 4) {
            return null;
        }
        type = "end";
        return { type, align, width };
    } else {
        spec = spec.slice(3);
    }
    // Standalone ":" should be treated as flex-end
    align = "flex-start";
    if (spec.endsWith(":")) {
        align = "flex-end";
        spec = spec.slice(0, -1);
        if (spec.startsWith(":")) {
            align = "center";
            spec = spec.slice(1);
        }
    } else if (spec.startsWith(":")) {
        spec = spec.slice(1);
    }
    let unit = "%";
    if (spec.endsWith("px")) {
        unit = "px";
        spec = spec.slice(0, -2);
    } else if (spec.endsWith("%")) {
        spec = spec.slice(0, -1);
    }
    if (!/^-?\d+$/.test(spec)) {
        width = "1fr";
    } else {
        const num = parseInt(spec, 10);
        width = isNaN(num) ? `1fr` : `${num}${unit}`;
    }
    return { type, align, width };
}

function formatNumber(num) {
    const rounded = Math.round(num * 10000) / 10000;
    return Number.isInteger(rounded) ? `${rounded}` : `${rounded}`.replace(/\.?0+$/, "");
}

function normalizeColumnWidths(entries) {
    const percentEntries = [];
    let percentTotal = 0;

    for (const entry of entries) {
        const width = entry.spec.width;
        const percentMatch = width.match(/^(\d+(?:\.\d+)?)%$/);
        if (percentMatch) {
            const value = Number(percentMatch[1]);
            if (Number.isFinite(value) && value > 0) {
                percentEntries.push(entry);
                percentTotal += value;
            }
        }
    }

    if (percentTotal > 100 && percentEntries.length > 0) {
        const scale = 100 / percentTotal;
        for (const entry of percentEntries) {
            const value = Number(entry.spec.width.replace("%", ""));
            entry.spec.width = `${formatNumber(value * scale)}%`;
        }
    }

    return entries;
}
function mergeColumnSpec(markdown) {
    let parts = markdown.split(columnRegex);
    let specIndex = {};
    for (let i = 0; i < parts.length; i++) {
    if (!columnRegex.test(parts[i])) {
        continue;
    }
    const spec = parseCulumnSpec(parts[i]);
    if (!spec) {
        continue;
    }
    switch (spec.type) {
        case "start":
            if (Object.keys(specIndex).length > 0) {
                specIndex = {};
            }
            specIndex[i] = spec;
            break;
        case "separator":
            if (Object.keys(specIndex).length === 0) {
                break;
            }
            specIndex[i] = spec;
            break;
        case "end":
            if (Object.keys(specIndex).length === 0) {
                break;
            }
            {
                const orderedSpecs = normalizeColumnWidths(
                    Object.keys(specIndex).map((index) => ({ index, spec: specIndex[index] }))
                );
                const cols = orderedSpecs.map(({ spec }) => `minmax(auto, ${spec.width})`).join(' ');
                let outerDiv = `

<div style="display: grid; grid-template-columns: ${cols}; gap: 20px; width: 100%; min-width: 0; box-sizing: border-box;">

`;
                for (const { index, spec: s } of orderedSpecs) {
                const innerDiv = `

<div style="display: flex; flex-direction: column; justify-content: ${s.align}; min-width: 0; max-width: 100%;">

`;
                parts[index] = outerDiv + innerDiv;
                outerDiv = `</div>`;
                }
                parts[i] = `</div></div>`;
                specIndex = {};
            }
            break;
        }
    }
    return parts.join("\n");
}
markdown = mergeColumnSpec(markdown);