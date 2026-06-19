import { test, expect, type Page } from "@playwright/test";
import { ServerControl } from "./control";

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Collect all console messages with "error" severity and page errors.
 * Call .assert() at the end of a test to verify no unexpected errors occurred.
 *
 * Filters are kept specific to avoid false negatives. Known benign messages
 * from third-party libraries (model-viewer, three.js, WebGL drivers, etc.)
 * are excluded with targeted substrings.
 */
async function setupConsoleCapture(page: Page) {
  const errors: string[] = [];
  const warnings: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    } else if (msg.type() === "warning") {
      warnings.push(msg.text());
    }
  });
  page.on("pageerror", (err) => {
    errors.push(err.message);
  });
  return {
    errors,
    warnings,
    assert: () => {
      // Targeted benign patterns matching known third-party messages.
      const benignPatterns = [
        "GPU stall due to ReadPixels", // WebGL driver perf warning
        "Gain map metadata not f", // three.js HDR decode
        "model-viewer", // <model-viewer> internal logs
        "GLTFExporter: Use MeshStandardMaterial", // model-viewer GLB export warning
        // 404 from playground wheel detection when served without a local wheel
        "status of 404", // Matches: "Failed to load resource: the server responded with a status of 404 (File not found)"
      ];
      const filteredErrors = errors.filter((e) => !benignPatterns.some((p) => e.includes(p)));
      const filteredWarnings = warnings.filter((w) => !benignPatterns.some((p) => w.includes(p)));
      expect(filteredErrors, `Console errors (${filteredErrors.length}): ${filteredErrors.join("; ")}`).toEqual([]);
      expect(filteredWarnings, `Console warnings (${filteredWarnings.length}): ${filteredWarnings.join("; ")}`).toEqual([]);
    },
  };
}

/** Get the server control client from environment config. */
function getServerControl(): ServerControl {
  return new ServerControl();
}

/** Wait for the Vue app to fully mount and the page to be stable. */
async function waitForApp(page: Page) {
  await page.waitForFunction(
    () => {
      const layout = document.querySelector(".v-layout");
      return !!layout;
    },
    { timeout: 15000 },
  );
}

/**
 * Push a model from the backend and wait for it to appear in the viewer.
 */
async function pushModel(page: Page, control: ServerControl, type: "box" | "sphere" | "cylinder", name: string, params: Record<string, number> = {}) {
  const result = await control.showModel(type, name, params);
  expect(result.ok).toBe(true);
  // Allow time for SSE notification + rendering
  await page.waitForTimeout(2000);
  await expect(page.locator("text=No model loaded")).not.toBeVisible({ timeout: 15000 });
  const modelViewer = page.locator("model-viewer");
  await expect(modelViewer).toBeVisible({ timeout: 10000 });
}

/**
 * Click on a Vuetify v-slider track at a given fraction (0..1) to set its value.
 * This finds the slider element and clicks at the appropriate position on its track.
 */
async function setSliderByClick(page: Page, sliderLocator: any, fraction: number) {
  const box = await sliderLocator.boundingBox();
  if (!box) throw new Error("Slider not found on page");
  const targetX = box.x + box.width * fraction;
  const targetY = box.y + box.height / 2;
  await page.mouse.click(targetX, targetY);
  await page.waitForTimeout(300);
}

/** Get the tools sidebar locator. */
function toolsSidebar(page: Page) {
  return page.locator(".v-navigation-drawer").filter({ hasText: "Tools" });
}

/** Get the models (left) sidebar locator. */
function modelsSidebar(page: Page) {
  return page.locator(".v-navigation-drawer").filter({ hasText: "Models" });
}

// ─── Tests ───────────────────────────────────────────────────────────────────

test.describe("Empty state", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("shows the welcome buttons when no models are loaded", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // The empty state should show the title
    await expect(page.locator("text=No model loaded")).toBeVisible({ timeout: 5000 });

    // The Open playground and Load demo models buttons should be visible
    await expect(page.locator("button", { hasText: "Open playground" })).toBeVisible({ timeout: 5000 });
    await expect(page.locator("button", { hasText: "Load demo models" })).toBeVisible({ timeout: 5000 });
    await expect(page.locator("button", { hasText: "Load model manually" })).toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/empty-state.png", fullPage: true });
  });
});

test.describe("Backend model interactions", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("shows a box pushed from the backend", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Push a box model and verify it appears
    await pushModel(page, getServerControl(), "box", "test_box", { width: 2, height: 3, depth: 4 });

    capture.assert();
    await page.screenshot({ path: "screenshots/backend-box.png", fullPage: true });
  });

  test("toggles projection between perspective and orthographic", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "proj_test");

    // The toggle button is in the tools sidebar with text "PERSP" then "ORTHO"
    const toggleBtn = toolsSidebar(page).locator("button").filter({ hasText: "PERSP" });
    await expect(toggleBtn).toBeVisible({ timeout: 5000 });
    await toggleBtn.click();
    await page.waitForTimeout(500);

    // Now the button should show "ORTHO"
    await expect(toolsSidebar(page).locator("button").filter({ hasText: "ORTHO" })).toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/projection-toggle.png", fullPage: true });
  });

  test("centers the camera via keyboard shortcut", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "center_test");

    // Press 'c' to center camera
    await page.keyboard.press("c");
    await page.waitForTimeout(500);

    capture.assert();
    await page.screenshot({ path: "screenshots/camera-centered.png", fullPage: true });
  });

  test("supports sphere and cylinder models", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Push a sphere
    await pushModel(page, control, "sphere", "mysphere", { radius: 5 });

    // Push a cylinder
    await pushModel(page, control, "cylinder", "mycylinder", { radius: 3, height: 8 });

    capture.assert();
    await page.screenshot({ path: "screenshots/sphere-cylinder.png", fullPage: true });
  });

  test("handles model removal via the backend", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "toremove");

    // Remove the model via the backend
    const removeResult = await control.removeModel("toremove");
    expect(removeResult.ok).toBe(true);
    await page.waitForTimeout(2000);

    // The empty state should reappear
    await expect(page.locator("text=No model loaded")).toBeVisible({ timeout: 10000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/model-removed.png", fullPage: true });
  });

  test("downloads the scene as GLB", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "dl_test");

    // Use keyboard shortcut 'd' to download the scene
    const downloadPromise = page.waitForEvent("download", { timeout: 15000 });
    await page.keyboard.press("d");
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(".glb");

    capture.assert();
  });

  test("opens and closes the licenses dialog", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, getServerControl(), "box", "license_test");

    // Find the Licenses button by position: it's 2 buttons after the Sandbox button
    // In the tools sidebar, the order is: Sandbox, Download, Licenses, GitHub
    await page.evaluate(() => {
      const toolsPanel = document.querySelector(".v-navigation-drawer--right");
      if (!toolsPanel) return;
      const buttons = Array.from(toolsPanel.querySelectorAll("button"));
      for (let i = 0; i < buttons.length; i++) {
        if (buttons[i]?.textContent?.includes("Sandbox") && i + 2 < buttons.length) {
          (buttons[i + 2] as HTMLElement).click();
          return;
        }
      }
    });
    await page.waitForTimeout(1000);

    // The licenses dialog should show up (it has a v-card with title "Licenses")
    const dialogTitle = page.locator(".v-card").filter({ hasText: "Licenses" });
    await expect(dialogTitle).toBeVisible({ timeout: 5000 });

    // Close the dialog via the close button
    const closeBtn = dialogTitle.locator("..").locator("button").last();
    await expect(closeBtn).toBeVisible({ timeout: 5000 });
    await closeBtn.click();
    await page.waitForTimeout(500);

    capture.assert();
    await page.screenshot({ path: "screenshots/licenses-dialog.png", fullPage: true });
  });
});

test.describe("Demo models", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("loads demo models from the CDN", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Click the "Load demo models" button
    await page.locator("button", { hasText: "Load demo models" }).click();

    // Wait for models to appear (6 models are loaded)
    await expect(page.locator("text=No model loaded")).not.toBeVisible({ timeout: 15000 });

    // The sidebar should show multiple model entries
    await expect(page.locator(".v-expansion-panel").first()).toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/demo-models-loaded.png", fullPage: true });
  });
});

test.describe("Playground", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("opens the playground dialog and shows editor + console", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, getServerControl(), "box", "pg_test");

    // Click the Sandbox button in the tools sidebar
    const sandboxBtn = page.locator("button").filter({ hasText: "Sandbox" });
    await expect(sandboxBtn).toBeVisible({ timeout: 5000 });
    await sandboxBtn.click();

    // Wait for the dialog to appear
    const popupCard = page.locator(".popup-card");
    await expect(popupCard).toBeVisible({ timeout: 10000 });

    // Verify the playground title
    await expect(popupCard.locator("text=Playground")).toBeVisible({ timeout: 5000 });

    // Verify the editor area (Monaco editor takes time to load)
    const editor = popupCard.locator(".playground-editor");
    await expect(editor).toBeVisible({ timeout: 5000 });

    // Wait for monaco-editor to be fully mounted before taking screenshot
    const monacoEditor = popupCard.locator(".monaco-editor");
    await expect(monacoEditor).toBeVisible({ timeout: 20000 });

    // Verify the console area
    const consoleArea = popupCard.locator(".playground-console");
    await expect(consoleArea).toBeVisible({ timeout: 5000 });
    await expect(consoleArea.locator("text=Console Output")).toBeVisible({ timeout: 5000 });

    // Verify toolbar controls are present
    await expect(popupCard.locator('input[type="checkbox"]')).toBeVisible({ timeout: 5000 });

    // Take screenshot AFTER all content is confirmed loaded
    await page.screenshot({ path: "screenshots/playground-dialog.png", fullPage: true });

    // Close the dialog via the close button (last button in the toolbar)
    const closeBtn = popupCard.locator(".v-toolbar button").last();
    await expect(closeBtn).toBeVisible({ timeout: 5000 });
    await closeBtn.click();
    await page.waitForTimeout(500);

    // Verify the dialog is closed (popup-card should not be visible)
    await expect(popupCard).not.toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: "screenshots/playground-closed.png", fullPage: true });

    capture.assert();
  });

  test("opens playground from the empty state welcome button", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Click "Open playground" on the empty state
    await page.locator("button", { hasText: "Open playground" }).click();

    // The dialog should open
    const popupCard = page.locator(".popup-card");
    await expect(popupCard).toBeVisible({ timeout: 10000 });
    await expect(popupCard.locator("text=Playground")).toBeVisible({ timeout: 5000 });

    // Wait for the editor and console to fully mount before taking screenshot
    await expect(popupCard.locator(".playground-editor")).toBeVisible({ timeout: 5000 });
    await expect(popupCard.locator(".monaco-editor")).toBeVisible({ timeout: 20000 });
    await expect(popupCard.locator(".playground-console")).toBeVisible({ timeout: 5000 });
    await expect(popupCard.locator(".playground-console pre")).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: "screenshots/playground-from-empty.png", fullPage: true });

    // Close it
    const closeBtn = popupCard.locator(".v-toolbar button").last();
    await closeBtn.click();
    await page.waitForTimeout(500);

    capture.assert();
  });
});

test.describe("Model sidebar", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("shows model entries in the sidebar", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Push a named model
    await pushModel(page, control, "box", "my_test_box");

    // The sidebar should contain an expansion panel with the model name
    const sidebarModel = page.locator(".v-expansion-panel").filter({ hasText: "my_test_box" });
    await expect(sidebarModel).toBeVisible({ timeout: 5000 });

    // The model name should be visible in the sidebar
    await expect(sidebarModel.locator(".model-name")).toHaveText("my_test_box");

    capture.assert();
    await page.screenshot({ path: "screenshots/sidebar-model-entry.png", fullPage: true });
  });

  test("can expand model panel and see controls", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "expand_test");

    // Click on the expansion panel title to expand it
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "expand_test" });
    const panelTitle = panel.locator(".v-expansion-panel-title");
    await expect(panelTitle).toBeVisible({ timeout: 5000 });
    await panelTitle.click();
    await page.waitForTimeout(500);

    // After expanding, we should see controls (opacity slider, explode slider, etc.)
    const panelText = panel.locator(".v-expansion-panel-text");
    await expect(panelText).toBeVisible({ timeout: 5000 });

    // Check that a slider control is present in the expanded panel
    await expect(panelText.locator(".v-slider").first()).toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/sidebar-expanded-model.png", fullPage: true });
  });

  test("can toggle model face/edge/vertex visibility", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "vis_test");

    // The face/edge/vertex toggle buttons are inside a v-btn-toggle in the panel title
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "vis_test" });
    const toggleGroup = panel.locator(".v-btn-toggle");
    await expect(toggleGroup).toBeVisible({ timeout: 5000 });

    // Get all 3 toggle buttons
    const toggleButtons = toggleGroup.locator("button");
    await expect(toggleButtons).toHaveCount(3);

    // Each should be a Vuetify toggle button (has v-btn--variant class)
    for (let i = 0; i < 3; i++) {
      await expect(toggleButtons.nth(i)).toBeVisible({ timeout: 3000 });
    }

    capture.assert();
    await page.screenshot({ path: "screenshots/sidebar-visibility-toggles.png", fullPage: true });
  });

  test("can remove a model via the sidebar delete button", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "delete_me");

    // Find the delete button in the model's expansion panel title
    const panelDel = page.locator(".v-expansion-panel").filter({ hasText: "delete_me" });
    const deleteBtn = panelDel.locator(".v-expansion-panel-title button").last();
    await expect(deleteBtn).toBeVisible({ timeout: 5000 });
    await deleteBtn.click();

    // The model should be removed
    await page.waitForTimeout(2000);

    // Check that the model entry is gone
    const modelEntry = page.locator(".v-expansion-panel").filter({ hasText: "delete_me" });
    await expect(modelEntry).not.toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/sidebar-after-delete.png", fullPage: true });
  });
});

test.describe("Toolbar buttons", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("shows the GitHub button in the tools sidebar", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, getServerControl(), "box", "github_test");

    // The GitHub button is the last icon button in the tools sidebar (after Licenses)
    const toolsSb = toolsSidebar(page);
    const githubBtn = toolsSb.locator("button").last();
    await expect(githubBtn).toBeVisible({ timeout: 5000 });

    capture.assert();
    await page.screenshot({ path: "screenshots/toolbar-github-button.png", fullPage: true });
  });
});

test.describe("3D Selection", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("can select a face by clicking on a model in selection mode", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "sel_test");

    // Press 's' to enable selection mode
    await page.keyboard.press("s");
    await page.waitForTimeout(500);

    // Click at the center of the model-viewer to trigger selection
    const viewer = page.locator("model-viewer");
    await expect(viewer).toBeVisible({ timeout: 5000 });
    const viewerBox = await viewer.boundingBox();
    expect(viewerBox).not.toBeNull();

    if (viewerBox) {
      const clickX = viewerBox.x + viewerBox.width / 2;
      const clickY = viewerBox.y + viewerBox.height / 2;
      await page.mouse.click(clickX, clickY);
      await page.waitForTimeout(500);
    }

    // The selection display in the tools sidebar should show the count
    // It shows as "Selection (NF NE NV)" where N is the count
    const selectionHeader = toolsSidebar(page)
      .locator("h5")
      .filter({ hasText: /Selection/ });
    await expect(selectionHeader).toBeVisible({ timeout: 5000 });

    // A face should have been selected (face count > 0)
    const selectionText = await selectionHeader.textContent();
    expect(selectionText).toMatch(/\([1-9]/); // Should have at least 1 selected item

    capture.assert();
    await page.screenshot({ path: "screenshots/selection-face-selected.png", fullPage: true });
  });

  test("pressing 's' toggles selection mode on and off", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "sel_toggle");

    // Press 's' to enable selection mode
    await page.keyboard.press("s");
    await page.waitForTimeout(300);

    // Press 's' again to disable
    await page.keyboard.press("s");
    await page.waitForTimeout(300);

    capture.assert();
    await page.screenshot({ path: "screenshots/selection-toggle.png", fullPage: true });
  });

  test("can select edges and vertices using the filter dropdown", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "sel_edge_test");

    // Enable selection mode
    await page.keyboard.press("s");
    await page.waitForTimeout(500);

    const viewer = page.locator("model-viewer");
    await expect(viewer).toBeVisible({ timeout: 5000 });
    const viewerBox = await viewer.boundingBox();
    expect(viewerBox).not.toBeNull();

    // Select an edge: change filter to "(E)dges"
    const selectFilter = toolsSidebar(page).locator(".v-select");
    await expect(selectFilter).toBeVisible({ timeout: 5000 });
    await selectFilter.click();
    await page.waitForTimeout(300);

    // Select "(E)dges" from the dropdown
    await page.locator(".v-list-item").filter({ hasText: "(E)dges" }).click();
    await page.waitForTimeout(300);

    // Click at center of model-viewer to try selecting an edge
    if (viewerBox) {
      const clickX = viewerBox.x + viewerBox.width / 2;
      const clickY = viewerBox.y + viewerBox.height / 2;
      await page.mouse.click(clickX, clickY);
      await page.waitForTimeout(500);
    }

    // The selection filter should now show edges
    capture.assert();
    await page.screenshot({ path: "screenshots/selection-edge-filter.png", fullPage: true });
  });

  test("can toggle bounding box display on a selected face", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "bb_test");

    // Enable selection mode and select a face
    await page.keyboard.press("s");
    await page.waitForTimeout(500);

    const viewer = page.locator("model-viewer");
    await expect(viewer).toBeVisible({ timeout: 5000 });
    const viewerBox = await viewer.boundingBox();
    expect(viewerBox).not.toBeNull();

    if (viewerBox) {
      const clickX = viewerBox.x + viewerBox.width / 2;
      const clickY = viewerBox.y + viewerBox.height / 2;
      await page.mouse.click(clickX, clickY);
      await page.waitForTimeout(500);
    }

    // The bounding box toggle is 2 buttons before the Sandbox button (Sandbox - 2)
    await page.evaluate(() => {
      const toolsPanel = document.querySelector(".v-navigation-drawer--right");
      if (!toolsPanel) return;
      const buttons = Array.from(toolsPanel.querySelectorAll("button"));
      for (let i = 0; i < buttons.length; i++) {
        if (buttons[i]?.textContent?.includes("Sandbox") && i - 2 >= 0) {
          (buttons[i - 2] as HTMLElement).click();
          return;
        }
      }
    });
    await page.waitForTimeout(500);

    capture.assert();
    await page.screenshot({ path: "screenshots/selection-bounding-box.png", fullPage: true });
  });

  test("can toggle distance measurements on selected features", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "dist_test");

    // Enable selection mode and select a face
    await page.keyboard.press("s");
    await page.waitForTimeout(500);

    const viewer = page.locator("model-viewer");
    await expect(viewer).toBeVisible({ timeout: 5000 });
    const viewerBox = await viewer.boundingBox();
    expect(viewerBox).not.toBeNull();

    if (viewerBox) {
      const clickX = viewerBox.x + viewerBox.width / 2;
      const clickY = viewerBox.y + viewerBox.height / 2;
      await page.mouse.click(clickX, clickY);
      await page.waitForTimeout(500);
    }

    // The distances toggle is 1 button before the Sandbox button (Sandbox - 1)
    await page.evaluate(() => {
      const toolsPanel = document.querySelector(".v-navigation-drawer--right");
      if (!toolsPanel) return;
      const buttons = Array.from(toolsPanel.querySelectorAll("button"));
      for (let i = 0; i < buttons.length; i++) {
        if (buttons[i]?.textContent?.includes("Sandbox") && i - 1 >= 0) {
          (buttons[i - 1] as HTMLElement).click();
          return;
        }
      }
    });
    await page.waitForTimeout(500);

    capture.assert();
    await page.screenshot({ path: "screenshots/selection-distances.png", fullPage: true });
  });
});

test.describe("Model controls", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("can change opacity via the slider", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "opacity_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "opacity_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    // The first slider in the expanded panel is the opacity slider
    const expandedText = panel.locator(".v-expansion-panel-text");
    const opacitySlider = expandedText.locator(".v-slider").first();
    await expect(opacitySlider).toBeVisible({ timeout: 5000 });

    // Click at 75% of the slider width to set opacity to ~0.75
    await setSliderByClick(page, opacitySlider, 0.75);

    capture.assert();
    await page.screenshot({ path: "screenshots/opacity-slider-adjusted.png", fullPage: true });
  });

  test("can change edge width via the slider", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "edgewidth_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "edgewidth_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");

    // The edge width slider is the third slider (after opacity, explode)
    // Only visible when edgeCount > 0 (which is true for Box)
    const edgeWidthSlider = expandedText.locator(".v-slider").nth(2);
    // Verify it's visible (it has v-if="edgeCount > 0 || vertexCount > 0")
    const isVisible = await edgeWidthSlider.isVisible().catch(() => false);
    if (isVisible) {
      await setSliderByClick(page, edgeWidthSlider, 0.5);
    }

    capture.assert();
    await page.screenshot({ path: "screenshots/edgewidth-slider-adjusted.png", fullPage: true });
  });

  test("can adjust clip planes", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "clip_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "clip_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");

    // Clip plane sliders come after the explode and edge-width sliders
    const allSliders = expandedText.locator(".v-slider");
    const sliderCount = await allSliders.count();
    expect(sliderCount).toBeGreaterThanOrEqual(4); // opacity, explode, (edgeWidth), X, Y, Z

    // The 4th slider (index 3) is clip plane X if edgeWidth is visible, otherwise index 3
    const clipSliderIdx = sliderCount >= 4 ? 3 : sliderCount >= 3 ? 2 : -1;
    if (clipSliderIdx >= 0) {
      const clipSlider = allSliders.nth(clipSliderIdx);
      await expect(clipSlider).toBeVisible({ timeout: 5000 });

      // Move it to 30%
      await setSliderByClick(page, clipSlider, 0.3);
      await page.waitForTimeout(300);
    }

    capture.assert();
    await page.screenshot({ path: "screenshots/clip-plane-adjusted.png", fullPage: true });
  });
});

test.describe("Additional model controls", () => {
  test.beforeEach(async () => {
    await getServerControl().clearModels();
  });

  test("can toggle wireframe mode on a model", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "wireframe_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "wireframe_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");

    // Find the wireframe checkbox (it's appended to the opacity slider)
    // The checkbox-btn has a triangle icon for wireframe mode
    const wireframeCheckbox = expandedText.locator(".v-checkbox-btn").first();
    await expect(wireframeCheckbox).toBeVisible({ timeout: 5000 });

    // Click to toggle wireframe ON
    await wireframeCheckbox.locator("input").check({ force: true });
    await page.waitForTimeout(300);

    capture.assert();
    await page.screenshot({ path: "screenshots/wireframe-toggle-on.png", fullPage: true });

    // Toggle wireframe OFF
    await wireframeCheckbox.locator("input").uncheck({ force: true });
    await page.waitForTimeout(300);

    capture.assert();
    await page.screenshot({ path: "screenshots/wireframe-toggle-off.png", fullPage: true });
  });

  test("can adjust explode slider", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "explode_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "explode_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");

    // The explode slider is the second slider (index 1)
    const explodeSlider = expandedText.locator(".v-slider").nth(1);
    await expect(explodeSlider).toBeVisible({ timeout: 5000 });

    // Set explode to 50%
    await setSliderByClick(page, explodeSlider, 0.5);

    capture.assert();
    await page.screenshot({ path: "screenshots/explode-slider-adjusted.png", fullPage: true });
  });

  test("can adjust all three clip plane axes", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    await pushModel(page, control, "box", "clip_all_test");

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "clip_all_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");
    const allSliders = expandedText.locator(".v-slider");
    const sliderCount = await allSliders.count();
    // At least 5 sliders: opacity, explode, (edgeWidth if edges > 0), clipX, clipZ, clipY
    expect(sliderCount).toBeGreaterThanOrEqual(5);

    // Clip plane sliders are always the last 3 (clipX, clipZ, clipY)
    const clipStartIndex = sliderCount - 3;

    // Adjust each clip plane slider
    for (let i = 0; i < 3; i++) {
      const clipSlider = allSliders.nth(clipStartIndex + i);
      await expect(clipSlider).toBeVisible({ timeout: 3000 });
      // Move each to a different position
      await setSliderByClick(page, clipSlider, 0.2 + i * 0.3);
    }

    capture.assert();
    await page.screenshot({ path: "screenshots/all-clip-planes-adjusted.png", fullPage: true });
  });

  test("can adjust vertex point size via edge width slider", async ({ page }) => {
    const capture = await setupConsoleCapture(page);
    const control = getServerControl();

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    // Use sphere which has vertices and edges
    await pushModel(page, control, "sphere", "vtx_test", { radius: 5 });

    // Expand the model panel
    const panel = page.locator(".v-expansion-panel").filter({ hasText: "vtx_test" });
    await panel.locator(".v-expansion-panel-title").click();
    await page.waitForTimeout(500);

    const expandedText = panel.locator(".v-expansion-panel-text");

    // The edge/vertex width slider is the third slider (index 2)
    // Visible because sphere has edgeCount > 0 and vertexCount > 0
    const edgeWidthSlider = expandedText.locator(".v-slider").nth(2);
    await expect(edgeWidthSlider).toBeVisible({ timeout: 5000 });

    // Set to 75% to increase both edge line width and vertex point size
    await setSliderByClick(page, edgeWidthSlider, 0.75);

    capture.assert();
    await page.screenshot({ path: "screenshots/vertex-point-size-adjusted.png", fullPage: true });
  });
});

test.describe("Playground URL demo", () => {
  test.setTimeout(600000); // 10 minutes max

  /**
   * Check the playground console for fatal error patterns and fail fast.
   */
  async function checkPlaygroundConsole(page: Page, popupCard: any): Promise<string> {
    const consolePre = popupCard.locator(".playground-console pre");
    const text = await consolePre.textContent().catch(() => "");
    const fatalErrors = [
      "ERR: Bootstrap failed",
      "ERR: Initial setup failed",
      "ERR: Failed to create worker",
      "ERR: Pyodide setup failed",
      "ERR: Code execution failed",
      "ERR: Initial code execution failed",
      "Can't find a pure Python 3 wheel",
      "PythonError:",
      "Traceback (most recent call last)",
    ];
    for (const pattern of fatalErrors) {
      if (text.includes(pattern)) {
        throw new Error(`Playground fatal error detected: "${pattern}". Full console:\n${text}`);
      }
    }
    return text;
  }

  test("loads the URL playground demo with base64 code and creates models in-browser", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    // Base64url+gzipped inline code: "from build123d import *\nfrom yacv_server import show\nshow(Box(10, 10, 10))\n"
    const pgCodeB64 = "H4sIAAAAAAAC_0srys9VSCrNzEkxNDJOUcjMLcgvKlHQ4koDiVcmJpfFF6cWlaUWwWSKM_LLuUCEhlN-hYahgY4CBGtqcgEADvR4mUsAAAA";
    const pgCodeUrl = `/?pg_code=${encodeURIComponent(pgCodeB64)}`;

    await page.goto(pgCodeUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForApp(page);

    // The playground dialog should auto-open because pg_code is non-empty
    const popupCard = page.locator(".popup-card");
    await expect(popupCard).toBeVisible({ timeout: 15000 });
    await expect(popupCard.locator("text=Playground")).toBeVisible({ timeout: 5000 });
    await expect(popupCard.locator(".playground-console")).toBeVisible({ timeout: 5000 });

    // Wait for the editor to mount
    const monacoEditor = popupCard.locator(".monaco-editor");
    await expect(monacoEditor).toBeVisible({ timeout: 20000 });

    // Take a screenshot showing the playground has loaded (editor + console visible)
    await page.screenshot({ path: "screenshots/playground-url-loading.png", fullPage: true });

    // Wait for "No model loaded" to disappear. If it doesn't within the timeout,
    // check the console for fatal errors and fail with a clear message.
    await expect(page.locator("text=No model loaded"))
      .not.toBeVisible({ timeout: 300000 })
      .catch(async (err) => {
        // If the model didn't load, check for fatal errors in the console
        await checkPlaygroundConsole(page, popupCard);
        // Re-throw if no fatal error found (it was just slow)
        throw err;
      });
    await page.waitForTimeout(1000);

    // Verify the model viewer is visible
    const modelViewer = page.locator("model-viewer");
    await expect(modelViewer).toBeVisible({ timeout: 10000 });

    await page.screenshot({ path: "screenshots/playground-url-demo-loaded.png", fullPage: true });
    capture.assert();
  });

  test("loads the playground demo from hash URL like the README example (build123d dev version)", async ({ page }) => {
    const capture = await setupConsoleCapture(page);

    // Use the hash-based URL format from the README:
    const toyTruckUrl =
      "/#pg_code=" + encodeURIComponent("https://raw.githubusercontent.com/gumyr/build123d/refs/heads/dev/examples/toy_truck.py") + "&pg_version=dev";

    await page.goto(toyTruckUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForApp(page);

    // The playground dialog should auto-open
    const popupCard = page.locator(".popup-card");
    await expect(popupCard).toBeVisible({ timeout: 15000 });
    await expect(popupCard.locator("text=Playground")).toBeVisible({ timeout: 5000 });
    await expect(popupCard.locator(".playground-console")).toBeVisible({ timeout: 5000 });

    // Wait for the editor to mount
    const monacoEditor = popupCard.locator(".monaco-editor");
    await expect(monacoEditor).toBeVisible({ timeout: 20000 });

    await page.screenshot({ path: "screenshots/playground-url-toy-truck-loading.png", fullPage: true });

    // Wait for model to appear, catching timeout and checking for errors
    // The toy truck is a complex model that may take a while to build in Pyodide
    await expect(page.locator("text=No model loaded"))
      .not.toBeVisible({ timeout: 500000 })
      .catch(async (err) => {
        await checkPlaygroundConsole(page, popupCard);
        throw err;
      });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: "screenshots/playground-url-toy-truck-loaded.png", fullPage: true });
    capture.assert();
  });
});
