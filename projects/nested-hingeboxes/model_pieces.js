// Write every piece of the 3D model, as model.html places it with the boxes nested
// and every lid closed, to JSON: for each box its walls and hinge pieces (outline,
// holes and the matrix that places the extruded outline) and its pins (radius,
// length and matrix), in the generator's frame (Z up).  check_model.py reads it.
// Needs Playwright with Chromium:  node projects/nested-hingeboxes/model_pieces.js [OUT.json]
// (default: stdout)
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.join(__dirname, "model.html"));
  await page.waitForSelector("#loading", { state: "hidden", timeout: 60000 });
  const boxes = await page.evaluate(() => {
    state.view = "nested";
    state.lid = 0;
    applyLid();
    applyLayout(true);
    boxes.forEach(bx => bx.group.position.copy(bx.pos));
    root.updateMatrixWorld(true);
    // undo root's turn to Y-up; three.js matrices are column-major arrays
    const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
    const place = mesh => new THREE.Matrix4().multiplyMatrices(inv, mesh.matrixWorld).toArray();
    return boxes.map(bx => {
      const of = kind => bx.meshes.filter(m => m.kind === kind).map(m => m.mesh);
      return {
        t: bx.b.t,
        pieces: of("wall").map((mesh, i) => {
          const p = bx.b.pieces[i];
          return { name: p.name, group: p.group, outline: p.outline, holes: p.holes, matrix: place(mesh) };
        }),
        hinge: { outline: bx.b.hinge.outline, holes: bx.b.hinge.holes },
        hinges: of("hinge").map((mesh, i) => ({ group: bx.b.hinges[i].group, matrix: place(mesh) })),
        pins: of("pin").map(mesh => ({ r: mesh.geometry.parameters.radiusTop,
                                       length: mesh.geometry.parameters.height, matrix: place(mesh) })),
      };
    });
  });
  await browser.close();
  const json = JSON.stringify({ boxes });
  if (process.argv[2]) fs.writeFileSync(process.argv[2], json);
  else process.stdout.write(json);
})();
